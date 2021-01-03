# Craftier

```
  ___  ____   __   ____  ____  __  ____  ____ (pre-α)
 / __)(  _ \ / _\ (  __)(_  _)(  )(  __)(  _ \
( (__  )   //    \ ) _)   )(   )(  ) _)  )   /
 \___)(__\_)\_/\_/(__)   (__) (__)(____)(__\_)

      Your personal Python code reviewer
```

## What is it?
Craftier is a framework to easily writing Python code refactors. In the near
future it will also come with a set of predefined refactoring rules.

It is based on `libcst` and simplifies the use of its API by letting you write
refactors just by writing Python code.

It also preserves relevant comments and ensures the modified code is correct, by
adding required parentheses.

## Getting started
After installing with `pip install craftier`, you can run the default rules with
`craftier refactor <python files>`.

## Configuration
By default we look for a `.craftier.ini`, if none is found a default
configuration will be used.

You can also specify the config file with `--config CONFIG_PATH`

### Config format

```ini
[craftier]
packages=craftier.refactors,
excluded=A,
         B
```

## Writing your own rules

As simple as:

```py
import craftier

class SquareTransformer(craftier.CraftierTransformer):
    def square_before(self, x):
        x * x

    def square_after(self, x):
        x ** 2


class IfTrueTransformer(craftier.CraftierTransformer):
    def if_true_before(self, x, y):
        x if True else y

    def if_true_after(self, x):
        x
```

TODO: write about custom matchers and type declarations

# Roadmap and TODOs
* Support multiple expressions in a transformer
* Add support for statements 
* Complete set of refactorings
* Add support for typing metadata
* Generate RE2 filtering based on expressions. This could be used to prefilter
  the list of files and to test the patterns either in codebase search tools
  like https://grep.app
* Extensive validation testing

## Limitations
This is a work in progress, and some edges are rough.

Given that we match code based on actual Python code, some refactorings are not
easily expressed or may not even be expressible at all.

## History
TODO: write how I came up with the idea.

### Name
Originally I wanted to name this package `pythonista`, but unfortunately someone
squatted the name (along with several others) and the name was not released
according to procedure. Furthermore, the issue was locked.

That gave me a chance of rethinking the name, so I started with anagrams of the
word `refactor`, which was of course unsuccessful. So after some
experimentation I replaced the letter `o` with an `i`, giving `refactir`, which
is an anagram of the word `craftier`.

I like that name, because is like a "refactoring" of the word `refactor`, and
`craftier` conveys the actual use case of the tool.

Bonus: the name sounds somewhat like my surname.