#!/usr/bin/python
# python3 runner.py <test_suite_sys_id>

import sys
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
import json
import time

# Filter ID to human-readable name mapping
FILTER_LOOKUP = {
    "4d26770a93b91a100d4d317a7bba10d6": "Choice of Medical Plan",
    # Add more mappings as needed
}

def get_filter_name(filter_id):
    """Get human-readable name for a filter ID"""
    return FILTER_LOOKUP.get(filter_id, filter_id)

def run_test_suite(instance_url, username, password, test_suite_sys_id):
    """Run a ServiceNow ATF test suite via REST API and monitor its progress"""
    
    url = f'{instance_url}/api/sn_cicd/testsuite/run'
    params = {'test_suite_sys_id': test_suite_sys_id}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # Trigger the test suite
    try:
        response = requests.post(
            url,
            auth=HTTPBasicAuth(username, password),
            headers=headers,
            params=params
        )
        
        response.raise_for_status()  # Raise an exception for bad status codes
        
        response_text = response.text
        if not response_text or not response_text.strip():
            print("Error: Empty response received from test suite trigger")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        sys.exit(1)

    if response.status_code == 200:
        print('Test suite triggered successfully')
        result = response.json().get('result', {})
        progress_url = result.get('links', {}).get('progress', {}).get('url')
        
        if progress_url:
            print('Monitoring test suite progress...')
            
            while True:
                try:
                    # Use the full progress URL and add headers
                    progress_response = requests.get(
                        progress_url,  # Use complete URL from response
                        auth=HTTPBasicAuth(username, password),
                        headers={"Content-Type": "application/json", "Accept": "application/json"}
                    )
                    
                    progress_response.raise_for_status()
                    
                    progress_text = progress_response.text
                    if not progress_text or not progress_text.strip():
                        print("Warning: Empty response received")
                        time.sleep(5)
                        continue
                        
                    try:
                        progress = progress_response.json().get('result', {})
                    except requests.exceptions.JSONDecodeError:
                        print(f"Error: Invalid JSON response: {progress_response.text[:200]}")
                        time.sleep(5)
                        continue
                    
                    status_label = progress.get('status_label', 'Unknown')
                    percent_complete = progress.get('percent_complete', 0)
                    print(f'Status: {status_label} ({percent_complete}%)')
                    
                    if status_label in ['Completed', 'Error', 'Successful']:
                        print("\n=== Test Suite Completed ===")
                        
                        # Get the suite result ID from the results link
                        results_link = progress.get('links', {}).get('results', {})
                        suite_result_id = results_link.get('id')
                        if not suite_result_id:
                            print("Error: No suite result ID found in results link")
                            break
                            
                        # Get test results for this specific suite run
                        test_results_url = f"{instance_url}/api/now/table/sys_atf_test_result"
                        test_results_params = {
                            'sysparm_query': f'parent.sys_idSTARTSWITH{suite_result_id}^ORDERBYorder',
                            'sysparm_fields': 'test_name,sys_id,status,start_time,end_time,duration,message,output,order,test_suite_result'
                        }
                        
                        print("\nRetrieving individual test results...")
                        test_results_response = requests.get(
                            test_results_url,
                            auth=HTTPBasicAuth(username, password),
                            headers=headers,
                            params=test_results_params
                        )
                        
                        if test_results_response.status_code == 200:
                            test_results = test_results_response.json().get('result', [])
                            print(f"\nFound {len(test_results)} tests in suite:")
                            print("-" * 50)
                            
                            for test in test_results:
                                test_id = test.get('sys_id', 'Unknown')
                                print(f"\nTest: {test.get('test_name', 'Unknown')}")
                                print(f"Test ID: {test_id}")
                                print(f"Status: {test.get('status', 'Unknown')}")
                                # print(f"Duration: {test.get('duration', 'Unknown')} seconds")
                                if test.get('message'):
                                    print(f"Message: {test.get('message')}")
                                if test.get('output'):
                                    print(f"Output: {test.get('output')}")
                                
                                # Get test result items
                                test_items_url = f"{instance_url}/api/now/table/sys_atf_test_result_item"
                                test_items_params = {
                                    'sysparm_query': f'test_result={test_id}^ORDERBYstep_number',
                                    'sysparm_fields': 'step_name,status,message,step_number,error_message,output,summary'
                                }
                                
                                test_items_response = requests.get(
                                    test_items_url,
                                    auth=HTTPBasicAuth(username, password),
                                    headers=headers,
                                    params=test_items_params
                                )
                                
                                if test_items_response.status_code == 200:
                                    test_items = test_items_response.json().get('result', [])
                                    if test_items:
                                        for item in test_items:
                                            output = item.get('output', '')
                                            if 'Assigned selected result:' in output:
                                                result_json = json.loads(output.split('Assigned selected result:')[1].strip())
                                                print("\n=== Selected Result ===")
                                                print(f"System ID: {result_json.get('sys_id', 'Unknown')}")
                                                print(f"Score: {result_json.get('score', 'Unknown')}")
                                                # print(f"Sample Text: {result_json.get('sample_text', 'Unknown')}")
                                                filter_id = result_json.get('filter', 'Unknown')
                                                filter_name = get_filter_name(filter_id)
                                                expected_id = result_json.get('expected', 'Unknown')
                                                expected_name = get_filter_name(expected_id)
                                                print(f"Filter: {filter_name} ({filter_id})")
                                                if 'expected' in result_json:
                                                    print(f"Expected: {expected_name} ({expected_id})")
                                
                                print("-" * 30)
                        
                        if test_results_response.status_code == 200:
                            # Print summary of all test steps
                            print("\n=== Test Steps Summary ===")
                            total_steps = 0
                            passed_steps = 0
                            failed_steps = 0
                            
                            for test in test_results:
                                test_items_url = f"{instance_url}/api/now/table/sys_atf_test_result_item"
                                test_items_params = {
                                    'sysparm_query': f'test_result={test.get("sys_id")}^ORDERBYstep_number',
                                    'sysparm_fields': 'step_name,status,message,step_number'
                                }
                                
                                test_items_response = requests.get(
                                    test_items_url,
                                    auth=HTTPBasicAuth(username, password),
                                    headers=headers,
                                    params=test_items_params
                                )
                                
                                if test_items_response.status_code == 200:
                                    items = test_items_response.json().get('result', [])
                                    for item in items:
                                        total_steps += 1
                                        if item.get('status') == 'success':
                                            passed_steps += 1
                                        else:
                                            failed_steps += 1
                            
                            if total_steps > 0:
                                print(f"Total Steps: {total_steps}")
                                print(f"Passed Steps: {passed_steps}")
                                print(f"Failed Steps: {failed_steps}")
                                print(f"Success Rate: {(passed_steps/total_steps*100):.1f}% \n")
                        else:
                            print(f"Failed to retrieve test results: {test_results_response.status_code}")
                        
                        break
                    
                    # Get the progress response data
                    progress_data = progress_response.json()
                    if 'result' in progress_data:
                        progress = progress_data['result']
                        status_label = progress.get('status_label', 'Unknown')
                        percent_complete = progress.get('percent_complete', 0)
                        print(f'Status: {status_label} ({percent_complete}%)')
                        
                        # Get the results link when available
                        results_link = progress.get('links', {}).get('results', {})
                        if results_link:
                            suite_result_id = results_link.get('id')
                            if suite_result_id:
                                return {
                                    'status': status_label,
                                    'percent_complete': percent_complete,
                                    'suite_result_id': suite_result_id
                                }
                        
                        if status_label in ['Completed', 'Error']:
                            print("\n=== Test Suite Completed ===")
                            break
                    else:
                        print(f"Error: Unexpected progress response format: {progress_data}")
                        break
                
                except requests.exceptions.RequestException as e:
                    print(f"Error monitoring progress: {e}")
                    time.sleep(5)  # Wait before retrying
                    continue
                
                time.sleep(5)
            
            # Print final test summary if available
            if 'test_results' in locals():
                print("\n=== Final Test Summary ===")
                total_tests = len(test_results)
                passed_tests = sum(1 for test in test_results if test.get('status') == 'success')
                failed_tests = total_tests - passed_tests
                
                print(f"Total Tests: {total_tests}")
                print(f"Passed Tests: {passed_tests}")
                print(f"Failed Tests: {failed_tests}")
                if total_tests > 0:
                    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
                print("-" * 30)
            
            return {'status': 'Failed', 'message': 'Test suite monitoring failed'}
        else:
            print('Progress URL not found in the response')
            return response.json()
    else:
        print(f'Failed to trigger test suite. Status code: {response.status_code}')
        print('Response:', response.text)
        sys.exit(1)

if __name__ == "__main__":
    load_dotenv()

    # Check required environment variables
    INSTANCE_URL = os.getenv('SERVICENOW_INSTANCE_URL')
    USERNAME = os.getenv('SERVICENOW_USERNAME')
    PASSWORD = os.getenv('SERVICENOW_PASSWORD')
    
    if not all([INSTANCE_URL, USERNAME, PASSWORD]):
        print("Error: Missing required environment variables.")
        print("Please ensure these are set in your .env file:")
        print("  SERVICENOW_INSTANCE_URL")
        print("  SERVICENOW_USERNAME")
        print("  SERVICENOW_PASSWORD")
        print("\nUsage: python3 runner.py <test_suite_sys_id>")
        print("Example: python3 runner.py 1234567890abcdef1234567890abcdef")
        sys.exit(1)

    if len(sys.argv) != 2:
        print("Error: Test suite sys_id is required")
        print("\nUsage: python3 runner.py <test_suite_sys_id>")
        print("Example: python3 runner.py 1234567890abcdef1234567890abcdef")
        sys.exit(1)

    test_suite_sys_id = sys.argv[1]
    
    result = run_test_suite(
        instance_url=INSTANCE_URL,
        username=USERNAME,
        password=PASSWORD,
        test_suite_sys_id=test_suite_sys_id
    )
    
    print("\nTest suite execution completed.")
