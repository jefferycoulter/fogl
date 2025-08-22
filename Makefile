# ---- toolchain ---------------------------------------------------------------
F90C          ?= gfortran
CC          ?= cc
PYTHON      ?= python3
PKG_CONFIG  ?= pkg-config

# ---- generator inputs --------------------------------------------------------
GL_XML      ?= gl.xml
GEN         ?= scripts/gen_gl_fortran.py
GL_VERSION  ?= 3.3
PROFILE     ?= core

BINDINGS       := gl_bindings_33.f90
DEMO_BINDINGS  := demo/$(notdir $(BINDINGS))
BINDINGS_MOD := demo/gl_bindings_33_core.mod

# ---- sources ----------------------------------------------------------------
C_SRCS      := c/gl_loader.c c/glfw_context.c
C_OBJS      := $(C_SRCS:.c=.o)

DEMO_F90_SRCS := $(DEMO_BINDINGS) demo/triangle.f90
DEMO_F90_OBJS := $(DEMO_F90_SRCS:.f90=.o)

BIN_DIR     := bin
DEMO_TARGET := $(BIN_DIR)/triangle_demo

FFLAGS := -Wall -Wextra -Jdemo -Idemo
CFLAGS := -Wall -Wextra

# ---- set flags -------------------------------------------
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    GLFW_CFLAGS := $(shell $(PKG_CONFIG) --cflags glfw3)
    GLFW_LIBS   := $(shell $(PKG_CONFIG) --libs   glfw3)
    CFLAGS      += $(GLFW_CFLAGS) -DGL_SILENCE_DEPRECATION
else
    GLFW_CFLAGS := $(shell $(PKG_CONFIG) --cflags glfw3)
    GLFW_LIBS   := $(shell $(PKG_CONFIG) --libs   glfw3)
    CFLAGS      += $(GLFW_CFLAGS)
endif
LDLIBS := $(GLFW_LIBS)

.PHONY: all
all: $(BINDINGS)

# generate bindings in root
$(BINDINGS): $(GL_XML) $(GEN)
	$(PYTHON) $(GEN) --xml $(GL_XML) --version $(GL_VERSION) --profile $(PROFILE) --out $(BINDINGS)

.PHONY: demo
demo: $(DEMO_TARGET)

# copy bindings into demo/
$(DEMO_BINDINGS): $(BINDINGS)
	@mkdir -p demo
	cp $< $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

demo/%.o: demo/%.f90
	$(F90C) $(FFLAGS) -c $< -o $@

# link final demo binary
$(DEMO_TARGET): $(BIN_DIR) $(C_OBJS) $(DEMO_F90_OBJS)
	$(F90C) -o $@ $(C_OBJS) $(DEMO_F90_OBJS) $(LDLIBS)

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

# ---- force regenerate ----------------------------------------
.PHONY: regen
regen:
	@echo ">> Forcing regeneration of bindings"
	$(RM) $(BINDINGS) $(DEMO_BINDINGS)
	$(PYTHON) $(GEN) --xml $(GL_XML) --version $(GL_VERSION) --profile $(PROFILE) --out $(BINDINGS)

# ---- utils -------------------------------------------------------------
.PHONY: run
run: demo
	./$(DEMO_TARGET)

.PHONY: clean
clean:
	$(RM) $(C_OBJS) $(DEMO_F90_OBJS) $(DEMO_TARGET) $(BINDINGS) $(DEMO_BINDINGS) $(BINDINGS_MOD)
	@rmdir $(BIN_DIR)
