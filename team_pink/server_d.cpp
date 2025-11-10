/**
 * @file server_d.cpp
 * @brief Process D - Team Pink Worker Server (C++)
 * 
 * Worker process that handles queries for Team Pink data subset
 * Note: D is shared between Team Green (B) and Team Pink (E)
 */

#include <iostream>
#include <memory>
#include <string>
#include <fstream>
#include <grpcpp/grpcpp.h>
#include <nlohmann/json.hpp>

#include "../proto/fire_service.grpc.pb.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;
using fire_service::FireQueryService;
using fire_service::QueryRequest;
using fire_service::QueryResponseChunk;
using fire_service::InternalQueryRequest;
using fire_service::InternalQueryResponse;
using fire_service::StatusRequest;
using fire_service::StatusResponse;
using json = nlohmann::json;

/**
 * @class FireQueryServiceImpl
 * @brief Implementation of FireQueryService for Process D (Worker)
 */
class FireQueryServiceImpl final : public FireQueryService::Service {
private:
    std::string process_id_;
    std::string role_;
    std::string team_;
    int port_;
    
    // TODO: Add FireColumnModel member variable

public:
    FireQueryServiceImpl(const json& config) {
        process_id_ = config["identity"];
        role_ = config["role"];
        team_ = config["team"];
        port_ = config["port"];
        
        std::cout << "[" << process_id_ << "] Initialized as " << role_ 
                  << " for Team " << team_ << std::endl;
        
        // TODO: Initialize FireColumnModel with Team Pink data subset
    }
    
    /**
     * Query RPC - Workers typically don't receive direct client queries
     */
    Status Query(ServerContext* context, 
                 const QueryRequest* request,
                 grpc::ServerWriter<QueryResponseChunk>* writer) override {
        std::cout << "[" << process_id_ << "] Received direct query request_id=" 
                  << request->request_id() << std::endl;
        
        // Return empty response
        QueryResponseChunk chunk;
        chunk.set_request_id(request->request_id());
        chunk.set_chunk_number(0);
        chunk.set_is_last_chunk(true);
        chunk.set_total_chunks(1);
        chunk.set_total_results(0);
        
        writer->Write(chunk);
        return Status::OK;
    }
    
    /**
     * InternalQuery RPC - Main method for workers
     * Receives queries from team leaders (Process B or E)
     */
    Status InternalQuery(ServerContext* context,
                        const InternalQueryRequest* request,
                        InternalQueryResponse* response) override {
        std::cout << "[" << process_id_ << "] Internal query from " 
                  << request->requesting_process() << std::endl;
        std::cout << "  Request ID: " << request->request_id() << std::endl;
        std::cout << "  Original request: " << request->original_request_id() << std::endl;
        std::cout << "  Query type: " << request->query_type() << std::endl;
        
        // TODO: Query local FireColumnModel data
        // TODO: Apply filters from request->filter()
        // TODO: Convert results to FireMeasurement proto messages
        
        // For now, return empty response
        response->set_request_id(request->request_id());
        response->set_original_request_id(request->original_request_id());
        response->set_is_complete(true);
        response->set_responding_process(process_id_);
        
        std::cout << "[" << process_id_ << "] Returning response with " 
                  << response->measurements_size() << " measurements" << std::endl;
        
        return Status::OK;
    }
    
    /**
     * CancelRequest RPC
     */
    Status CancelRequest(ServerContext* context,
                        const StatusRequest* request,
                        StatusResponse* response) override {
        std::cout << "[" << process_id_ << "] Cancel request_id=" 
                  << request->request_id() << std::endl;
        
        response->set_request_id(request->request_id());
        response->set_status("cancelled");
        response->set_chunks_delivered(0);
        response->set_total_chunks(0);
        
        return Status::OK;
    }
    
    /**
     * GetStatus RPC
     */
    Status GetStatus(ServerContext* context,
                    const StatusRequest* request,
                    StatusResponse* response) override {
        std::cout << "[" << process_id_ << "] Status request_id=" 
                  << request->request_id() << std::endl;
        
        response->set_request_id(request->request_id());
        response->set_status("pending");
        response->set_chunks_delivered(0);
        response->set_total_chunks(0);
        
        return Status::OK;
    }
    
    /**
     * Notify RPC
     */
    Status Notify(ServerContext* context,
                 const InternalQueryRequest* request,
                 StatusResponse* response) override {
        std::cout << "[" << process_id_ << "] Notification from " 
                  << request->requesting_process() << std::endl;
        
        response->set_request_id(request->request_id());
        response->set_status("acknowledged");
        
        return Status::OK;
    }
};

/**
 * Load configuration from JSON file
 */
json load_config(const std::string& config_path) {
    std::ifstream file(config_path);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open config file: " + config_path);
    }
    
    json config;
    file >> config;
    return config;
}

/**
 * Start the gRPC server
 */
void RunServer(const std::string& config_path) {
    // Load configuration
    json config = load_config(config_path);
    std::string process_id = config["identity"];
    std::string hostname = config["hostname"];
    int port = config["port"];
    
    // Build server address
    std::string server_address = hostname + ":" + std::to_string(port);
    
    // Create service implementation
    FireQueryServiceImpl service(config);
    
    // Build and start server
    ServerBuilder builder;
    builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);
    
    std::unique_ptr<Server> server(builder.BuildAndStart());
    std::cout << "[" << process_id << "] Server started on " << server_address << std::endl;
    std::cout << "[" << process_id << "] Press Ctrl+C to stop" << std::endl;
    
    // Wait for server shutdown
    server->Wait();
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <config_file>" << std::endl;
        std::cerr << "Example: " << argv[0] << " ../configs/process_d.json" << std::endl;
        return 1;
    }
    
    try {
        RunServer(argv[1]);
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}

