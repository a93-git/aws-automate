"""
Create a python object with agents' status for each instance

Master Lambda -> At end of final invocation -> send input data to this function -
                                                                                |
parse it <- Create its input structure <- check each agent's status on each VM <-
  |
  -> create file structure -> update the JSON with data for each VM


Input: A dictionary with region wise agent data for each agent

Values for status:
    0 - installation failed
    1 - installation successful
    2 - installation timed-out
    3 - not applicable/couldn't find data for this agent for this particular 
        VM (no tags for that particular agent)

Input structure:

{
    "AgentName1": {
        "RegionName1": {
            "i-0948dj39848485": 1,
            "i-3748djdk3847dj": 0,
        ...
        },
        "RegionName2": {
            "i-0948dj39848485": 2,
            "i-3748djdk3847dj": 0,
        ...
        },
        ...
    },
    "AgentName2": {
        "RegionName1": {
            ...
        },
        ...
    },
    ...
}

Action: Parse data for each instance id for all the agents and create a JSON object

Output: Write the data for each instance to the JSON file in S3 bucket (region wise files)

Agent status list structure:
[Site24x7, Trend, DesktopCentral, Commvault] == [1,0,1,2]

File structure:

{
    "RegionName1": {
        "i-0948dj39848485": [1,2,0,3],
        "i-3748djdk3847dj": [0,1,0,1],
        ...
    },
    "RegionName2": {
        "i-0948dj39848485": [1,2,0,3],
        "i-3748djdk3847dj": [0,1,0,1],
        ...
    },
    ...
}

Sample code to convert input structure to file structure:

for agent in a.keys():
    for region in a[agent].keys():
        out[region] = {}
        for instance in a[agent][region].keys():
            out[region][instance] = []

for agent in a.keys():
    for region in a[agent].keys():
        for instance in a[agent][region].keys():
            out[region][instance].append(a[agent][region][instance])


TODO: Fix the missing key error when not all instance ids are there for all the agents
"""

# agent_status_data = {}
# agent_status_data['Site24x7'] = {}
# agent_status_data['Site24x7']['ap-southeast-1'] = {}
# agent_status_data['Site24x7']['ap-southeast-1']['instance-id'] = 0,1,2

# a = {"Site24x7": {"us-east-2": {}, "us-east-1": {}, "us-west-1": {}, "us-west-2": {}, "ap-south-1": {}, "ap-northeast-3": {}, "ap-northeast-2": {}, "ap-southeast-1": {}, "ap-southeast-2": {}, "ap-northeast-1": {}, "ca-central-1": {}, "eu-central-1": {}, "eu-west-1": {}, "eu-west-2": {}, "eu-west-3": {}, "eu-north-1": {}, "sa-east-1": {}}, "DesktopCentral": {"us-east-2": {}, "us-east-1": {}, "us-west-1": {}, "us-west-2": {}, "ap-south-1": {}, "ap-northeast-3": {}, "ap-northeast-2": {}, "ap-southeast-1": {}, "ap-southeast-2": {}, "ap-northeast-1": {}, "ca-central-1": {}, "eu-central-1": {}, "eu-west-1": {}, "eu-west-2": {}, "eu-west-3": {}, "eu-north-1": {}, "sa-east-1": {}}, "TrendMicro": {"us-east-2": {}, "us-east-1": {}, "us-west-1": {}, "us-west-2": {}, "ap-south-1": {}, "ap-northeast-3": {}, "ap-northeast-2": {}, "ap-southeast-1": {}, "ap-southeast-2": {}, "ap-northeast-1": {}, "ca-central-1": {}, "eu-central-1": {}, "eu-west-1": {}, "eu-west-2": {}, "eu-west-3": {}, "eu-north-1": {}, "sa-east-1": {}}, "Commvault": {"us-east-2": {}, "us-east-1": {}, "us-west-1": {}, "us-west-2": {}, "ap-south-1": {}, "ap-northeast-3": {}, "ap-northeast-2": {}, "ap-southeast-1": {}, "ap-southeast-2": {}, "ap-northeast-1": {}, "ca-central-1": {}, "eu-central-1": {}, "eu-west-1": {}, "eu-west-2": {}, "eu-west-3": {}, "eu-north-1": {}, "sa-east-1": {}}}

a = {'Site24x7': {'us-east-2': {}, 'us-east-1': {}, 'us-west-1': {}, 'us-west-2': {}, 'ap-south-1': {}, 'ap-northeast-3': {}, 'ap-northeast-2': {}, 'ap-southeast-1': {'i-0e01fe24bab69141b': 1, 'i-04f21375f6b03aa88': 1, 'i-07aa96b28c0e3e584': 1, 'i-08677f49b747cabbf': 1}, 'ap-southeast-2': {}, 'ap-northeast-1': {}, 'ca-central-1': {}, 'eu-central-1': {}, 'eu-west-1': {'i-07bf7e6314fecc07c': 1, 'i-04cb6a801f340f3ef': 1, 'i-0a25dc0cbeaba6f38': 1, 'i-0b9726a76a04feb8d': 1}, 'eu-west-2': {}, 'eu-west-3': {}, 'eu-north-1': {}, 'sa-east-1': {}}, 'DesktopCentral': {'us-east-2': {}, 'us-east-1': {}, 'us-west-1': {}, 'us-west-2': {}, 'ap-south-1': {}, 'ap-northeast-3': {}, 'ap-northeast-2': {}, 'ap-southeast-1': {'i-0e01fe24bab69141b': 1, 'i-04f21375f6b03aa88': 1, 'i-07aa96b28c0e3e584': 1, 'i-08677f49b747cabbf': 1}, 'ap-southeast-2': {}, 'ap-northeast-1': {}, 'ca-central-1': {}, 'eu-central-1': {}, 'eu-west-1': {'i-07bf7e6314fecc07c': 1}}}
out = {}

for agent in a.keys():
    for region in a[agent].keys():
        out[region] = {}
        for instance in a[agent][region].keys():
            out[region][instance] = []

for agent in a.keys():
    for region in a[agent].keys():
        for instance in a[agent][region].keys():
            out[region][instance].append(a[agent][region][instance])

print(out)