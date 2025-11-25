#!/usr/bin/env python3
"""
Test script for RAG API Server
Tests all endpoints to ensure the integration is working correctly
"""

import requests
import json
import sys

API_URL = "http://localhost:5000"

def test_health():
    """Test health check endpoint"""
    print("\n" + "="*70)
    print("Testing Health Check Endpoint")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Server is healthy")
            print(f"  Embeddings loaded: {data.get('embeddings_loaded')}")
            print(f"  Circuits available: {data.get('circuits_available')}")
            return True
        else:
            print(f"✗ Health check failed")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Is it running?")
        print(f"  Start it with: cd add && ./start_rag_server.sh")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_simple_query():
    """Test simple query endpoint"""
    print("\n" + "="*70)
    print("Testing Simple Query Endpoint")
    print("="*70)
    
    query = "What is a resistor?"
    print(f"Query: {query}")
    
    try:
        response = requests.post(
            f"{API_URL}/simple-query",
            json={"query": query},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✓ Query successful")
                print(f"\nResponse:")
                print(f"  {data.get('response')[:200]}...")
                return True
            else:
                print(f"✗ Query failed: {data.get('error')}")
                return False
        else:
            print(f"✗ HTTP Error {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_circuit_query():
    """Test circuit generation endpoint"""
    print("\n" + "="*70)
    print("Testing Circuit Generation Endpoint")
    print("="*70)
    
    query = "Create a simple LED circuit"
    print(f"Query: {query}")
    
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={"query": query},
            timeout=60
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✓ Circuit generation successful")
                
                if 'retrieved_circuits' in data:
                    print(f"\nRetrieved circuits:")
                    for circuit in data['retrieved_circuits'][:3]:
                        print(f"  - {circuit.get('name')} (similarity: {circuit.get('similarity'):.3f})")
                
                if 'circuit_text' in data:
                    circuit_text = data['circuit_text']
                    print(f"\nCircuit text length: {len(circuit_text)} characters")
                    print(f"First 100 chars: {circuit_text[:100]}...")
                    
                    # Save to file for inspection
                    with open('test_generated_circuit.txt', 'w') as f:
                        f.write(circuit_text)
                    print(f"✓ Circuit saved to test_generated_circuit.txt")
                
                return True
            else:
                print(f"✗ Circuit generation failed: {data.get('error')}")
                return False
        else:
            print(f"✗ HTTP Error {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("RAG API Server Integration Tests")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    
    if results[0][1]:  # Only continue if health check passes
        results.append(("Simple Query", test_simple_query()))
        results.append(("Circuit Generation", test_circuit_query()))
    
    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n✓ All tests passed! RAG integration is working correctly.")
        print("\nYou can now:")
        print("1. Build CircuitJS1: ./dev.sh")
        print("2. Open in browser and click 'AI Assistant' -> 'Open AI Chatbot'")
        print("3. Start asking questions or requesting circuits!")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
