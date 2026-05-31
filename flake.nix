{
  description = "Command-line tool for the HomeWizard P1 Meter";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
      in
      {
        packages.default = python.pkgs.buildPythonApplication {
          pname = "homewizard-cli";
          version = "0.2.0";
          pyproject = true;

          src = ./.;

          propagatedBuildInputs = with python.pkgs; [
            typer
            httpx
            pydantic
            rich
            zeroconf
          ];

          passthru.optional-dependencies = with python.pkgs; {
            ws = [ websockets ];
            json = [ orjson ];
            mqtt = [ paho-mqtt ];
          };

          meta = with pkgs.lib; {
            description = "Command-line tool for the HomeWizard P1 Meter";
            homepage = "https://github.com/SwordfishTrumpet/homewizard-cli";
            license = licenses.mit;
            mainProgram = "homewizard-cli";
          };
        };

        devShells.default = pkgs.mkShell {
          packages = [
            python
            python.pkgs.pip
            python.pkgs.uv
          ];
          inputsFrom = [ self.packages.${system}.default ];
        };
      }
    );
}
