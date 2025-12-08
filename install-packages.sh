#!/bin/bash

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir" || exit 1

if [ ! -d "git-pm" ]; then
    echo "Downloading git-pm..."
    curl -L -o git-pm.tar.gz https://github.com/Warrenn/git-pm/releases/download/v0.1.3/git-pm-0.1.3.tar.gz
    mkdir -p git-pm
    tar -xzf git-pm.tar.gz -C git-pm --strip-components=1
    rm git-pm.tar.gz
    echo "git-pm downloaded."
fi

echo "Installing packages via git-pm..."

python3 "$script_dir/git-pm/git-pm.py" install

echo "Installation complete."