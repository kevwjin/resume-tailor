{
  description = "Local resume-tailor CLI development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { nixpkgs, ... }:
    let
      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          python = pkgs.python312;
          tex = pkgs.texlive.combine {
            inherit (pkgs.texlive)
              scheme-small
              latexmk
              fontawesome5
              enumitem
              marvosym
              preprint
              titlesec;
          };
        in
        {
          default = pkgs.mkShell {
            packages = [
              python
              pkgs.uv
              tex
            ];

            shellHook = ''
              export XDG_CACHE_HOME="$PWD/.cache"
              export HF_HOME="$PWD/.cache/huggingface"
              export SENTENCE_TRANSFORMERS_HOME="$PWD/.cache/sentence-transformers"
            '';
          };
        });
    };
}
