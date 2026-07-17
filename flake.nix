{
  description = "Equalizer Python development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };

        dependencies = with pkgs; [
          stdenv.cc.cc
          libsndfile
          portaudio
          libGL
          glib
          libx11
          libxrender
          libxext
          libxi
          libxtst
          libsm
          libice
          libxcb
          libxcb-wm
          libxcb-image
          libxcb-keysyms
          libxcb-render-util
          xcb-util-cursor
          libxcb-util
          zstd
          libxkbcommon
          fontconfig
          freetype
          dbus
          zlib
        ];
      in
      {
        packages.default = pkgs.writeShellScriptBin "equalizer" ''
          GIT_ROOT=$(${pkgs.git}/bin/git rev-parse --show-toplevel 2>/dev/null || pwd)

          if [ ! -d "$GIT_ROOT/.venv" ]; then
            echo "Creating virtual environment at $GIT_ROOT/.venv..."
            ${pkgs.python3}/bin/python3 -m venv "$GIT_ROOT/.venv"
            source "$GIT_ROOT/.venv/bin/activate"
            pip install --upgrade pip setuptools wheel
            pip install -r ${./requirements.txt}
          else
            source "$GIT_ROOT/.venv/bin/activate"
          fi

          export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath dependencies}:$LD_LIBRARY_PATH

          python "$GIT_ROOT/code/main.py" "$@"
        '';

        devShells.default = pkgs.mkShell {
          name = "equalizer-dev-shell";

          buildInputs = with pkgs; [
            python3
            libsndfile
            portaudio
            git
          ];

          shellHook = ''
            # Find git root
            GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

            # Create virtual environment if it doesn't exist at the git root
            if [ ! -d "$GIT_ROOT/.venv" ]; then
              echo "Creating virtual environment at $GIT_ROOT/.venv..."
              python3 -m venv "$GIT_ROOT/.venv"
            fi

            # Activate virtual environment
            source "$GIT_ROOT/.venv/bin/activate"

            # Upgrade pip, setuptools, and wheel
            pip install --upgrade pip setuptools wheel

            # Install requirements relative to the flake.nix file
            echo "Installing Python packages from requirements.txt..."
            pip install -r ${./requirements.txt}

            # Set LD_LIBRARY_PATH so binary wheels (like PySide6, numpy, sounddevice, soundfile) can find required system libraries on NixOS
            export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath dependencies}:$LD_LIBRARY_PATH

            echo "Dev environment loaded! Python virtual environment activated."
          '';
        };

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/equalizer";
        };
      }
    );
}
