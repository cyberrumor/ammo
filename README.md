# oom
Obviously Organizes Mods

# Goals
- Made primarily for Linux
- Written in Rust
- Works with Skyrim
- Easy to build

# Dependencies
- Rust

# Build instructions
```
git clone https://github.com/cyberrumor/oom
cd oom
cargo build --release
```

# Installation instructions
```
sudo cp target/release/oom /usr/local/bin
mkdir -p ~/.local/share/applications
cp oom.desktop ~/.local/share/applications
```
