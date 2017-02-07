# Script for automated creation of F5 Big IP Virtual servers

## Requirements
`f5-icontrol-rest==1.3.0
f5-sdk==2.2.2
PyYAML==3.12
requests==2.12.5
six==1.10.0`

## Execution

python3 f5_bigip_helper.py config.yml [clean]
  clean - will delete all objects cpecified in config
