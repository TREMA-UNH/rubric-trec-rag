{
  description = "rubric-trec-rag";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-24.05";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.dspy-nix.url = "git+https://git.smart-cactus.org/ben/dspy-nix";
  inputs.exampp.url = "git+ssh://git@git.smart-cactus.org/ben/exampp.git";

  outputs = inputs@{ self, nixpkgs, flake-utils, dspy-nix, exampp, ... }:
    flake-utils.lib.eachDefaultSystem (system: 
      let
        pkgs = nixpkgs.legacyPackages.${system};

        mkShell = target: (dspy-nix.lib.${system}.mkShell {
          inherit target;
          pythonOverrides = [ exampp.lib.${system}.pythonOverrides ];
          packages = ps: [ ps.exampp ps.scikit-learn ps.mypy ps.pylatex ps.duckdb ];
        });

      in {
        packages.duckdb = pkgs.duckdb;
        packages.exampp = (pkgs.python3.override {packageOverrides = exampp.lib.${system}.pythonOverrides;}).pkgs.exampp;
        devShells.default = self.outputs.devShells.${system}.cuda;
        devShells.cpu = mkShell "cpu";
        devShells.rocm = mkShell "rocm";
        devShells.cuda = mkShell "cuda";
      }
    );

  nixConfig = {
    substituters = [ "https://dspy-nix.cachix.org" ];
    trusted-public-keys = [ "dspy-nix.cachix.org-1:VJ553D0iJVoA8ov2+ly+dLnGHarfSQpemzVW6dY6CfE=" ];
  };
}
