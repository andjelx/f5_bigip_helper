# Script for automated creation of F5 Big IP Virtual servers

## Requirements
```
f5-icontrol-rest==1.3.0
f5-sdk==2.2.2
PyYAML==3.12
requests==2.12.5
six==1.10.0
```
## Execution

```
python script.py [-b base_config.yml] config.yml [--clean]
```
clean - will delete all objects cpecified in config
config.yml parameters will be applied over base_config.yml if exists

Change log:
0.2 - Added split between baseconfig and user confing which applies on baseconfig parameters