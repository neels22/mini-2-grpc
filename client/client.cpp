/**
 * @file client.cpp
 * @brief C++ gRPC client for Fire Query Service
 * 
 * This client connects to Process A (Gateway) and sends queries
 * for fire air quality data, receiving results as a stream of chunks.
 */

#include <iostream>
#include <memory>
#include <string>
#include <grpcpp/grpcpp.h>

#include "../proto/fire_service.grpc.pb.h"
#include "../proto/fire_service.pb.h"

using grpc::Channel;
using grpc::ClientContext;
using grpc::Status;
using fire_service::FireQueryService;
using fire_service::QueryRequest;
using fire_service::QueryResponseChunk;
using fire_service::QueryFilter;
using fire_service::StatusRequest;
using fire_service::StatusResponse;

/**
 * @class FireQueryClient
 * @brief Client for interacting with the Fire Query Service
 */
class FireQueryClient {
public:
    /**
     * @brief Constructor - creates a client connected to the given server address
     * @param server_address Address of the server (e.g., "localhost:50051")
     */
    FireQueryClient(std::shared_ptr<Channel> channel)
        : stub_(FireQueryService::NewStub(channel)) {}

    /**
     * @brief Send a query and receive streaming results
     * @param request_id Unique request identifier
     * @param parameters List of parameters to query (e.g., "PM2.5", "PM10")
     * @param min_aqi Minimum AQI filter
     * @param max_aqi Maximum AQI filter
     */
    void Query(int64_t request_id, 
               const std::vector<std::string>& parameters,
               int32_t min_aqi, 
               int32_t max_aqi) {
        
        std::cout << "\n=== Sending Query ===" << std::endl;
        std::cout << "Request ID: " << request_id << std::endl;
        std::cout << "Parameters: ";
        for (const auto& param : parameters) {
            std::cout << param << " ";
        }
        std::cout << std::endl;
        std::cout << "AQI range: " << min_aqi << " - " << max_aqi << std::endl;
        
        // Create request
        QueryRequest request;
        request.set_request_id(request_id);
        request.set_query_type("filter");
        request.set_require_chunked(true);
        request.set_max_results_per_chunk(100);
        
        // Set filters
        QueryFilter* filter = request.mutable_filter();
        for (const auto& param : parameters) {
            filter->add_parameters(param);
        }
        filter->set_min_aqi(min_aqi);
        filter->set_max_aqi(max_aqi);
        
        // Create context
        ClientContext context;
        
        // Call the RPC and receive stream
        std::unique_ptr<grpc::ClientReader<QueryResponseChunk>> reader(
            stub_->Query(&context, request));
        
        // Read all chunks
        QueryResponseChunk chunk;
        int total_measurements = 0;
        
        while (reader->Read(&chunk)) {
            std::cout << "\n--- Received Chunk #" << chunk.chunk_number() << " ---" << std::endl;
            std::cout << "  Measurements in chunk: " << chunk.measurements_size() << std::endl;
            std::cout << "  Total results: " << chunk.total_results() << std::endl;
            std::cout << "  Total chunks: " << chunk.total_chunks() << std::endl;
            std::cout << "  Is last chunk: " << (chunk.is_last_chunk() ? "Yes" : "No") << std::endl;
            
            // Print first few measurements as examples
            int count = std::min(3, chunk.measurements_size());
            for (int i = 0; i < count; i++) {
                const auto& measurement = chunk.measurements(i);
                std::cout << "  Sample measurement " << (i + 1) << ":" << std::endl;
                std::cout << "    Site: " << measurement.site_name() << std::endl;
                std::cout << "    Parameter: " << measurement.parameter() << std::endl;
                std::cout << "    Concentration: " << measurement.concentration() 
                          << " " << measurement.unit() << std::endl;
                std::cout << "    AQI: " << measurement.aqi() << std::endl;
            }
            
            if (chunk.measurements_size() > 3) {
                std::cout << "  ... and " << (chunk.measurements_size() - 3) 
                          << " more measurements" << std::endl;
            }
            
            total_measurements += chunk.measurements_size();
        }
        
        // Check status
        Status status = reader->Finish();
        if (status.ok()) {
            std::cout << "\n✓ Query completed successfully" << std::endl;
            std::cout << "Total measurements received: " << total_measurements << std::endl;
        } else {
            std::cout << "\n✗ Query failed: " << status.error_code() << ": " 
                      << status.error_message() << std::endl;
        }
    }

    /**
     * @brief Get the status of a request
     * @param request_id Request ID to check
     */
    void GetStatus(int64_t request_id) {
        std::cout << "\n=== Checking Status ===" << std::endl;
        std::cout << "Request ID: " << request_id << std::endl;
        
        StatusRequest request;
        request.set_request_id(request_id);
        request.set_action("status");
        
        StatusResponse response;
        ClientContext context;
        
        Status status = stub_->GetStatus(&context, request, &response);
        
        if (status.ok()) {
            std::cout << "Status: " << response.status() << std::endl;
            std::cout << "Chunks delivered: " << response.chunks_delivered() 
                      << "/" << response.total_chunks() << std::endl;
        } else {
            std::cout << "Error: " << status.error_code() << ": " 
                      << status.error_message() << std::endl;
        }
    }

    /**
     * @brief Cancel a request
     * @param request_id Request ID to cancel
     */
    void CancelRequest(int64_t request_id) {
        std::cout << "\n=== Cancelling Request ===" << std::endl;
        std::cout << "Request ID: " << request_id << std::endl;
        
        StatusRequest request;
        request.set_request_id(request_id);
        request.set_action("cancel");
        
        StatusResponse response;
        ClientContext context;
        
        Status status = stub_->CancelRequest(&context, request, &response);
        
        if (status.ok()) {
            std::cout << "Status: " << response.status() << std::endl;
        } else {
            std::cout << "Error: " << status.error_code() << ": " 
                      << status.error_message() << std::endl;
        }
    }

private:
    std::unique_ptr<FireQueryService::Stub> stub_;
};


int main(int argc, char** argv) {
    std::string server_address = "localhost:50051";
    
    // Allow custom server address from command line
    if (argc > 1) {
        server_address = argv[1];
    }
    
    std::cout << "Fire Query Service C++ Client" << std::endl;
    std::cout << "==============================" << std::endl;
    std::cout << "Connecting to: " << server_address << std::endl;
    
    // Create channel
    FireQueryClient client(
        grpc::CreateChannel(server_address, grpc::InsecureChannelCredentials())
    );
    
    // Test 1: Query for PM2.5 and PM10 data
    std::vector<std::string> parameters = {"PM2.5", "PM10"};
    client.Query(12345, parameters, 0, 100);
    
    // Test 2: Get status
    client.GetStatus(12345);
    
    // Test 3: Cancel request
    client.CancelRequest(12345);
    
    std::cout << "\n=== All tests completed ===" << std::endl;
    
    return 0;
}

