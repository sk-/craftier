import contextlib
import dataclasses
import inspect
from typing import (
    Dict,
    Generator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Protocol,
    Sequence,
    Type,
    Union,
)

import libcst
import libcst.codemod
import libcst.metadata
from loguru import logger


class _LeaveMethod(Protocol):
    __self__: "ContextAwareTransformer"
    __name__: str
    __qualname__: str

    def __call__(
        self, original_node: libcst.CSTNodeT, updated_node: libcst.CSTNodeT
    ) -> Union[libcst.CSTNodeT, libcst.RemovalSentinel]:
        ...


CONTEXT_KEY = "craftier"


class ContextAwareTransformer(libcst.codemod.Codemod, libcst.CSTTransformer):
    """A lean replacement of libcst.codemod.ContextAwareTransformer.

    It just extends from `libcst.CSTTransformer` and not
    `libcst.matchers.MatcherDecoratableTransformer`, which reduces the checks
    performed when visiting nodes.
    """

    def __init__(self, context: libcst.codemod.CodemodContext) -> None:
        libcst.codemod.Codemod.__init__(self, context)
        libcst.CSTTransformer.__init__(self)

    def transform_module_impl(self, tree: libcst.Module) -> libcst.Module:
        return tree.visit(self)

    def get_leave_funcs(self) -> Mapping[str, _LeaveMethod]:
        """Return all the valid on_leave methods."""
        methods = inspect.getmembers(
            self,
            lambda m: (
                inspect.ismethod(m)
                and m.__name__.startswith("leave_")
                and not getattr(m, "_is_no_op", False)
            ),
        )

        return dict(methods)


class BatchedCodemod(libcst.codemod.Codemod, libcst.CSTTransformer):
    """Codemod which runs multiple transforms at the same time."""

    def __init__(
        self,
        context: libcst.codemod.CodemodContext,
        transformers: Sequence[Type[ContextAwareTransformer]],
        max_executions: int = 10,
    ):
        libcst.codemod.Codemod.__init__(self, context)
        libcst.CSTTransformer.__init__(self)
        self.max_executions = max_executions
        self.leave_methods: MutableMapping[str, List[_LeaveMethod]] = {}
        self.transformers = transformers
        self._batched_transformer: Optional[_BatchedTransformer] = None

    def transform_module_impl(self, tree: libcst.Module) -> libcst.Module:
        """Transform the tree.

        Note: we do not use should_allow_multiple_passes, as that approach
        compares the trees using an expensive deep compare operation. Instead,
        we use the information stored in the context by our transforms.

        This allow us to shave about 10% of the run time.
        """
        if not self._batched_transformer:
            leave_methods: Dict[str, List[_LeaveMethod]] = {}
            for transform_class in self.transformers:
                for name, method in (
                    transform_class(self.context).get_leave_funcs().items()
                ):
                    leave_methods.setdefault(
                        name.replace("leave_", ""), []
                    ).append(method)
            self._batched_transformer = _BatchedTransformer(leave_methods)

        self._batched_transformer.update_children_context(self.context)

        logger.debug("Checking {}", self.context.filename)
        was_modified = False
        modified_tree = tree
        for _ in range(self.max_executions):
            self._mark_as_not_modified()
            modified_tree = modified_tree.visit(self._batched_transformer)
            if not self._modified():
                break
            was_modified = True

        # This is a hack to avoid converting an umodified tree to code. This
        # improves the running time by about 10%.
        if not was_modified:
            raise libcst.codemod.SkipFile()
        logger.debug("Modified {}", self.context.filename)
        return modified_tree

    @contextlib.contextmanager
    def _handle_metadata_reference(
        self, module: libcst.Module
    ) -> Generator[libcst.Module, None, None]:
        """Optimize the speed of the orginal _handle_metadata_reference.

        Given that we know that CraftierTransform generate always different
        nodes, we can avoid the copy of the whole tree when building the
        metadata. This is an important performance optimization.
        """
        oldwrapper = self.context.wrapper
        metadata_manager = self.context.metadata_manager
        filename = self.context.filename
        if metadata_manager and filename:
            # We can look up full-repo metadata for this codemod!
            cache = metadata_manager.get_cache_for_path(filename)
            wrapper = libcst.metadata.MetadataWrapper(
                module, cache=cache, unsafe_skip_copy=True
            )
        else:
            # We are missing either the repo manager or the current path,
            # which can happen when we are codemodding from stdin or when
            # an upstream dependency manually instantiates us.
            wrapper = libcst.metadata.MetadataWrapper(
                module, unsafe_skip_copy=True
            )

        with self.resolve(wrapper):
            self.context = dataclasses.replace(self.context, wrapper=wrapper)
            try:
                yield wrapper.module
            finally:
                self.context = dataclasses.replace(
                    self.context, wrapper=oldwrapper
                )

    def _mark_as_not_modified(self) -> None:
        context = self.context.scratch.setdefault(CONTEXT_KEY, {})
        context[self.context.filename] = False

    def _modified(self) -> bool:
        context = self.context.scratch.get(CONTEXT_KEY, {})
        return bool(context[self.context.filename])


class _BatchedTransformer(libcst.CSTTransformer):
    def __init__(
        self,
        leave_methods: MutableMapping[str, List[_LeaveMethod]],
    ):
        libcst.CSTTransformer.__init__(self)
        self.leave_methods = leave_methods

    def on_visit(self, node: libcst.CSTNode) -> bool:
        return True

    def on_leave(
        self, original_node: libcst.CSTNodeT, updated_node: libcst.CSTNodeT
    ) -> Union[libcst.CSTNodeT, libcst.RemovalSentinel]:
        new_updated_node: Union[
            libcst.CSTNodeT, libcst.RemovalSentinel
        ] = updated_node
        original_node_type = type(original_node)
        for on_leave in self.leave_methods.get(original_node_type.__name__, []):
            # We use type here to detect whether the returned node is still
            # processable by these methods.
            # pylint: disable=unidiomatic-typecheck
            if type(updated_node) != original_node_type:
                break
            new_updated_node = on_leave(original_node, new_updated_node)
            # pylint: enable=unidiomatic-typecheck

        return new_updated_node

    def on_visit_attribute(self, node: libcst.CSTNode, attribute: str) -> None:
        return None

    def on_leave_attribute(
        self, original_node: libcst.CSTNode, attribute: str
    ) -> None:
        return None

    def update_children_context(
        self, context: libcst.codemod.CodemodContext
    ) -> None:
        """Propagate the context of the codemod to all children.

        There is some sort of a hack in the LibCST CLI interfaces which change
        the context of an existing codemod, but that does not get propagated all
        the way down.
        """
        for methods in self.leave_methods.values():
            for method in methods:
                method.__self__.context = context
