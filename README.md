# ServiceNow Semantic Validator                                                                              
                                                                                                              
Automatically test ServiceNow sensitivity filter through the Automated Test Framework (ATF) API.             
                                                                                                              
## Features                                                                                                  
                                                                                                              
- Run ServiceNow ATF test suites via REST API                                                                
- Monitor test execution progress in real-time                                                               
- Detailed test results including individual test steps                                                      
- Support for filter mapping and human-readable names                                                        
- Docker support for containerized execution                                                                 
                                                                                                              
## Prerequisites                                                                                             
                                                                                                              
- Python 3.11 or higher                                                                                      
- ServiceNow instance with ATF enabled                                                                       
- Access credentials for ServiceNow instance                                                                 
                                                                                                              
## Installation                                                                                              
                                                                                                              
1. Clone the repository:                                                                                     
```bash                                                                                                      
git clone https://github.com/antonekingservicenow/sn-semantic-validator.git                                  
cd sn-semantic-validator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your ServiceNow credentials:
```
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your-username
SERVICENOW_PASSWORD=your-password
```

4. Update Filter Lookup:
In `runner.py`, update the `FILTER_LOOKUP` dictionary with your filter mappings:
```python
FILTER_LOOKUP = {
    "4d26770...": "Medical Plan",
    # Add your filter sys_ids and their human-readable names here
}
```
Each filter sys_id should map to a human-readable name for better test result readability.

## Running with Docker

1. Build the Docker image:
```bash
docker build -t sn-filter-runner .
```

2. Run the Docker container:
```bash
docker run --env-file .env sn-filter-runner <test_suite_sys_id>
```

Replace `<test_suite_sys_id>` with your actual test suite ID. The `.env` file should contain your ServiceNow credentials and will be used to configure the environment inside the Docker container.
