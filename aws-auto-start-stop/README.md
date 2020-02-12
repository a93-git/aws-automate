# aws-auto-start-stop

## What?
Scripts for starting/stopping instances based on tags

## How?
1. Retrieves a list of instances matching the given tag key and tag value
2. Stops or starts those instances based on which script is run

## Why?
Stop AWS resources when not in use to save on costs

## Requirements
1. Python 3.x
2. Boto3 package

## Usage
Add the following to crontab:
<pre><code><em>[cron expression for time]</em> python3 startEC2Instances.py</pre></code>
<pre><code><em>[cron expression for time]</em> python3 stopEC2Instances.py</pre></code>


## Todo
1. ~Send SNS notification~
2. Improve error handling
3. ~Pass tag keys and tag values as arguments~
4. ~Add script to retrieve RDS instances based on given tag key and tag value~
5. ~Add start/stop script for RDS~
