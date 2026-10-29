# SALodLights only. macOS host, 32-bit Windows target, Homebrew mingw-w64
# (i686-w64-mingw32-g++, GCC 16). Game sources are not modified.
#
#   brew install mingw-w64
#   make -C mingw
#   make -C mingw CONFIG=debug
#   make -C mingw clangd

HERE := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
ROOT := $(abspath $(HERE)/..)
CXX := i686-w64-mingw32-g++
CC := i686-w64-mingw32-gcc
RC := i686-w64-mingw32-windres
CONFIG ?= release

ifeq ($(CONFIG),debug)
OUT := $(ROOT)/build/mingw/debug
CFG_FLAGS := -g -O0 -DDEBUG -D_DEBUG
RC_FLAGS := -D_DEBUG
else ifeq ($(CONFIG),release)
OUT := $(ROOT)/build/mingw/release
CFG_FLAGS := -O2 -g0 -DNDEBUG
RC_FLAGS :=
else
$(error CONFIG must be release or debug)
endif

GEN := $(ROOT)/build/mingw/gen
ASI := $(OUT)/SALodLights.asi

INCLUDES := \
	-I$(GEN) \
	-I$(ROOT)/includes \
	-I$(ROOT)/source \
	-I$(ROOT)/source/SALodLights \
	-I$(ROOT)/external/FusionFixUtils/include \
	-I$(ROOT)/external/FusionFixUtils \
	-I$(ROOT)/external/hooking \
	-I$(ROOT)/external/injector/safetyhook/include \
	-I$(ROOT)/external/injector/zydis \
	-I$(ROOT)/external/injector/include \
	-I$(ROOT)/external/IniReader \
	-I$(ROOT)/external/ModUtils

# 32-bit MinGW otherwise compares floats in x87 80-bit precision, so 0.05f
# does not match the game's 32-bit value and ProceduralDistance::Validate fails.
CXXFLAGS := -std=c++23 -msse2 -mfpmath=sse -fms-extensions -Wno-unknown-pragmas \
	-D_CRT_SECURE_NO_WARNINGS -DNOMINMAX -DUNICODE -D_UNICODE \
	$(CFG_FLAGS) $(INCLUDES)
CFLAGS := -O2 -g0 -DNDEBUG $(INCLUDES)
ifeq ($(CONFIG),debug)
CFLAGS := -g -O0 -DDEBUG -D_DEBUG $(INCLUDES)
endif
STRIP := i686-w64-mingw32-strip

SAFETYHOOK := $(wildcard $(ROOT)/external/injector/safetyhook/src/*.cpp)
SAFETYHOOK_OBJ := $(patsubst $(ROOT)/external/injector/safetyhook/src/%.cpp,$(OUT)/safetyhook/%.o,$(SAFETYHOOK))
OBJS := $(OUT)/SALodLights.o $(OUT)/Hooking.Patterns.o $(OUT)/Zydis.o $(SAFETYHOOK_OBJ)
LIBS := -ld3d9 -lpsapi -lshell32 -lole32 -luuid -lshlwapi -luser32

SA_SRC := $(wildcard $(ROOT)/source/*.ixx) $(wildcard $(ROOT)/source/SALodLights/*.ixx) \
	$(ROOT)/source/SALodLights/dllmain.cpp $(ROOT)/source/LightVolumes.ps \
	$(ROOT)/includes/stdafx.h $(ROOT)/external/hooking/Hooking.Patterns.cpp \
	$(ROOT)/external/IniReader/IniReader.h \
	$(ROOT)/external/FusionFixUtils/include/gameref.hpp \
	$(ROOT)/external/FusionFixUtils/include/callbacks.h \
	$(ROOT)/source/SALodLights/Settings.rc $(ROOT)/resources/VersionInfo.rc \
	$(wildcard $(ROOT)/settings/SALodLights*.json)

.PHONY: all clean clangd
all: $(ASI)

clangd: $(GEN)/SALodLights.cpp
	python3 $(HERE)/clangd.py

$(ASI): $(OBJS) $(OUT)/SALodLights.res
	$(CXX) -shared -static -static-libgcc -static-libstdc++ -Wl,--kill-at -Wl,--subsystem,windows -o $@ $(OBJS) $(OUT)/SALodLights.res $(LIBS)
ifeq ($(CONFIG),release)
	$(STRIP) --strip-debug $@
endif
	@if [ -f "$(ROOT)/.env" ]; then \
		dir=$$(sed -n 's/^[[:space:]]*GTA_SAN_ANDREAS_DIR[[:space:]]*=[[:space:]]*//p' "$(ROOT)/.env" | head -1); \
		dir=$${dir%\"}; dir=$${dir#\"}; dir=$${dir%\'}; dir=$${dir#\'}; dir=$${dir%/}; \
		if [ -n "$$dir" ] && [ -f "$$dir/scripts/SALodLights.asi" ]; then \
			cp -f "$@" "$$dir/scripts/SALodLights.asi"; \
			echo "installed $$dir/scripts/SALodLights.asi"; \
		fi; \
	fi

$(OUT)/SALodLights.o: $(GEN)/SALodLights.cpp
	@mkdir -p $(OUT)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OUT)/Hooking.Patterns.o: $(GEN)/Hooking.Patterns.cpp
	@mkdir -p $(OUT)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OUT)/Zydis.o: $(ROOT)/external/injector/zydis/Zydis.c
	@mkdir -p $(OUT)
	$(CC) $(CFLAGS) -c $< -o $@

$(OUT)/safetyhook/%.o: $(ROOT)/external/injector/safetyhook/src/%.cpp
	@mkdir -p $(OUT)/safetyhook
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OUT)/SALodLights.res: $(GEN)/rc/SALodLights.rc $(GEN)/rc/VersionInfo.rc $(GEN)/rc/VersionInfo.h
	$(RC) $(RC_FLAGS) -I$(GEN)/rc -O coff -o $@ $<

$(GEN)/SALodLights.cpp: $(HERE)/prepare.py $(SA_SRC) $(HERE)/LightVolumes.cso.hex
	python3 $(HERE)/prepare.py

$(GEN)/Hooking.Patterns.cpp $(GEN)/rc/SALodLights.rc: $(GEN)/SALodLights.cpp
	@test -f $@

clean:
	rm -rf $(ROOT)/build/mingw $(ROOT)/build/clangd
