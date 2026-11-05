# VeyraOS — common tasks. `make help` lists them.
SHELL := /bin/bash
.DEFAULT_GOAL := help

help:  ## Show this help
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-16s %s\n", $$1, $$2}'

iso:  ## Build the ISO in an Artix container (needs Docker + internet)
	build/build-in-docker.sh

iso-native:  ## Build the ISO on an Artix host (as root)
	sudo build/build-iso.sh

test: test-static test-unit  ## Fast tests (no containers)

test-static:  ## Version consistency, desktop files, JSON, shellcheck
	tests/static/check-static.sh
	tests/static/shellcheck-all.sh

test-unit:  ## Python unit + GUI smoke tests (needs PySide6)
	python3 -m pytest -q tests/unit

test-packaging:  ## Build + install all VeyraOS packages in Artix containers
	tests/packaging/build-and-install.sh

test-boot:  ## QEMU live-boot test (BIOS/UEFI/copytoram/verify/textmode)
	tests/boot/run-boot-test.sh

test-desktop: test-packaging  ## Render the desktop in Plasma 6 and take screenshots
	tests/desktop/run-plasma-test.sh

test-all: test test-packaging test-boot test-desktop  ## Everything

assets:  ## Regenerate artwork (wallpapers, sounds, GRUB/Plymouth images, decorations, kdeglobals)
	tools/gen-wallpapers.py src/branding/wallpapers
	tools/gen-sounds.py src/branding/sounds
	tools/gen-branding.py
	tools/gen-aurorae.py src/desktop/usr/share/aurorae/themes
	tools/gen-kdeglobals.py

.PHONY: help iso iso-native test test-static test-unit test-packaging test-boot test-desktop test-all assets
