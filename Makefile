# Makefile for Fire Query C++ Servers (if needed)
# Note: All servers are currently implemented in Python
# This Makefile is kept for potential future C++ server implementations

CXX = clang++
CXXFLAGS = -std=c++17 -stdlib=libc++ -I. -Icommon -I/opt/homebrew/include
LDFLAGS = -L/opt/homebrew/lib -stdlib=libc++
# Link all libraries - abseil, grpc, protobuf, re2
ABSL_LIBS = $(shell find /opt/homebrew/lib -name 'libabsl_*.dylib' -exec basename {} .dylib \; | sed 's/^lib/-l/' | tr '\n' ' ')
LIBS = -lgrpc++ -lgrpc -lprotobuf -lre2 $(ABSL_LIBS) -lupb -laddress_sorting -lgpr -lpthread -lz -lm

# Source files (C++ server implementations - currently not used)
SERVER_C_SRC = team_green/server_c.cpp
SERVER_D_SRC = team_pink/server_d.cpp
SERVER_F_SRC = team_pink/server_f.cpp
PROTO_SRC = proto/fire_service.pb.cc proto/fire_service.grpc.pb.cc

# Outputs
SERVER_C_OUT = build/server_c
SERVER_D_OUT = build/server_d
SERVER_F_OUT = build/server_f

.PHONY: all clean servers

all: servers

servers: $(SERVER_C_OUT) $(SERVER_D_OUT) $(SERVER_F_OUT)

$(SERVER_C_OUT): $(SERVER_C_SRC) $(PROTO_SRC)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) $(SERVER_C_SRC) $(PROTO_SRC) -o $(SERVER_C_OUT) $(LDFLAGS) $(LIBS)
	@echo "✓ Built server C: $(SERVER_C_OUT)"

$(SERVER_D_OUT): $(SERVER_D_SRC) $(PROTO_SRC)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) $(SERVER_D_SRC) $(PROTO_SRC) -o $(SERVER_D_OUT) $(LDFLAGS) $(LIBS)
	@echo "✓ Built server D: $(SERVER_D_OUT)"

$(SERVER_F_OUT): $(SERVER_F_SRC) $(PROTO_SRC)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) $(SERVER_F_SRC) $(PROTO_SRC) -o $(SERVER_F_OUT) $(LDFLAGS) $(LIBS)
	@echo "✓ Built server F: $(SERVER_F_OUT)"
	@echo ""
	@echo "======================================"
	@echo "Build complete!"
	@echo "======================================"
	@echo "Executables:"
	@echo "  Server C: $(SERVER_C_OUT)"
	@echo "  Server D: $(SERVER_D_OUT)"
	@echo "  Server F: $(SERVER_F_OUT)"
	@echo ""
	@echo "Note: C++ servers are not currently implemented."
	@echo "All servers are Python-based. See:"
	@echo "  team_green/server_c.py"
	@echo "  team_pink/server_d.py"
	@echo "  team_pink/server_f.py"
	@echo ""

clean:
	rm -rf build
	@echo "Build directory cleaned"

