# mononoki

> [!WARNING]
> This is a vibe coded fork that fixes some spacing and size issues experienced on Windows.

> A font for programming and code review.

For a closer look [http://madmalik.github.io/mononoki/](http://madmalik.github.io/mononoki/).

## Features

- Alternate stylistic set with dotted zero, configurable with `ss01`.

## Installation

[Download mononoki.zip](https://github.com/madmalik/mononoki/releases/download/1.6/mononoki.zip) and unpack it.

- [macOS](http://support.apple.com/kb/HT2509), alternatively there is also a [homebrew formula](https://github.com/Homebrew/homebrew-cask/blob/main/Casks/font/font-m/font-mononoki.rb).
- [Windows](https://support.microsoft.com/en-us/office/add-a-font-b7c5f17c-4426-4b53-967f-455339c564c1)
- Linux/Unix - distro dependent, if you have a font manager installed on your system, open the font file and hit "Install". Alternatively, there are [mononoki-packages](https://repology.org/project/fonts:mononoki/versions) in many of the package repos, if you prefer installing via package manager.

## Building

`export/` is generated from the UFOs in `src/` (needs `nix`, or fontforge, ttfautohint, fonttools and nerd-font-patcher on `PATH`):

```sh
nix-shell --run ./build.sh          # export/mononoki-*.{otf,ttf}
nix-shell --run './build.sh --nerd' # also export/nerd/MononokiNerdFontMono-*.ttf
```

Bold and Bold Italic are generated from Regular and Italic so they keep exactly the same heights (approach from [monofoki](https://github.com/datMaffin/monofoki)).

## Credit

Box drawing characters created with [box drawing](https://github.com/adobe-type-tools/box-drawing).
