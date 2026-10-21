FROM archlinux:latest

# Update the system and install development tools
RUN pacman -Syu --noconfirm && \
    pacman -S --needed --noconfirm \
        base-devel \
        rust \
        cargo \
        cmake \
        ninja \
        git \
        gdb \
        clang \
        lldb \
        pkgconf \
        python \
        python-pip \
        nasm \
        yasm \
        make \
        wget \
        curl \
        unzip \
        zip \
        file \
        binutils \
        diffutils \
        patch \
        which \
        sudo \
        ca-certificates \
        sdl3 \
        vulkan-devel \
        libx11 \
        libxcursor \
        libxrandr \
        libxi \
        libxinerama \
        libxkbcommon \
        wayland \
        mesa \
        alsa-lib \
        libxss \
        libxtst \
        jack \
        pipewire \
        libpulse \
        sndio && \
    pacman -Scc --noconfirm

# The decomp's text generator (run by crates/decomp-c/build.rs) needs PyYAML.
RUN pip install --break-system-packages pyyaml

# Pre-download the Rust crate registry (registry cache, git deps and crate
# sources) into the image, so `cargo build` does not have to fetch anything on
# the first run. Only the manifests and Cargo.lock are copied: the layer stays
# cached until the dependency set changes. Adding a workspace member or a new
# dependency means rebuilding the image (`./tools/do`), which refreshes it.
COPY --parents Cargo.toml Cargo.lock crates/*/Cargo.toml /tmp/cargo-prefetch/
RUN cd /tmp/cargo-prefetch && \
    for crate in crates/*/; do \
        mkdir -p "$crate/src"; \
        : > "$crate/src/lib.rs"; \
        : > "$crate/src/main.rs"; \
        : > "$crate/build.rs"; \
    done && \
    CARGO_HOME=/opt/cargo cargo fetch --locked && \
    cd / && rm -rf /tmp/cargo-prefetch

# `tools/do` runs the container as the user that invoked it (so the files it
# writes into the bind-mounted /dw1, such as target/, belong to that user).
# Cargo still writes a few small files into CARGO_HOME at run time, so the
# prefetched registry and the home directory must be writable by an arbitrary
# uid: /opt/cargo holds the registry and /home/dw1 is the container's HOME.
RUN chmod -R a+rwX /opt/cargo && \
    mkdir -p /home/dw1 && \
    chmod 1777 /home/dw1

ENV PATH="/dw1:${PATH}"
VOLUME /dw1
WORKDIR /dw1
