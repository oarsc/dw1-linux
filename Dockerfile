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

COPY decomp/requirements.txt /tmp/decomp-requirements.txt
RUN pip install --break-system-packages -r /tmp/decomp-requirements.txt

ENV PATH="/dw1:${PATH}"
VOLUME /dw1
WORKDIR /dw1
