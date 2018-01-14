# AWS CloudWatch Log Clean

Some simple scripts for cleaning AWS CloudWatch Logs. Useful for cleaning up after AWS Lambda Functions. AWS doesn't seem to have nice rotation and cleanup for these. Leading to extremely degraded performance for CloudWatch metric "tailing".

**Notice:** These are destructive operations that will result in lost data if used incorrectly. I'm not responsible for any of your data that gets lost. I have personally tested these scripts and have used them as part of a maintenance procedure, but I don't guarantee they will work perfectly for you. Look over the scripts before running they, they're hopefully pretty straight forward.

## Installation

Ensure you have boto3: `pip install -y boto3`

These are just little helpers scripts and it isn't on Pypi or anything, just grab the zip:

```bash
wget -O aws-loudwatch-log-clean.zip https://github.com/four43/aws-cloudwatch-log-clean/archive/master.zip \
  && unzip ./aws-loudwatch-log-clean.zip
```

Or copy/paste the raw files into your own `.py` file. They don't depend on anything except `boto3`

## Usage

### nuke_log_group.py

This delete a log group and replace it with a new one with the same settings. This essentially clears all log streams from the log group. Usage:

```bash
./nuke_log_group.py [log-stream-prefix] --dry-run
```

Check that everything looks good, then:

```bash
./nuke_log_group.py [log-stream-prefix]
```

**Example:**

```bash
./nuke_log_group.py /aws/lambda/my-func
```

### sweep_log_streams.py

This will clean up old and empty log streams inside of a log group. Usage:

```bash
./sweep_log_streams.py [log-stream-prefix] --dry-run
```

Check that everything looks good, then:

```bash
./sweep_log_streams.py [log-stream-prefix]
```


Example:

```bash
./sweep_log_streams.py /aws/lambda/my-func
```

## Contributing

Feedback, issues, forks, and pull requests welcome! Thanks.