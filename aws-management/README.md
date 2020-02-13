# Example

```python
import listresorces

ec2_obj = listresources.EC2Info('bf6c34dc-4e7e-11ea-b7d1-02c84e6f15e0', 'arn:aws:iam::630125610951:role/test-ro', duration_seconds=1800, role_session_name='test-session')

ec2_obj.get_ec2_info()
```