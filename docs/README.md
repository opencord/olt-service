# vOLT Service Configuration

When you create the OLT Service in your profile there are few things that you may need to configure
they are described in this TOSCA recipe that you can customize and use (default values are displayed):

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
description: Set up VOLT service
imports:
  - custom_types/voltservice.yaml

topology_template:
  node_templates:
    service#volt:
      type: tosca.nodes.VOLTService
      properties:
        # Service Name
        name: volt
        
        # Informations on how to reach VOLTHA
        voltha_url: voltha.voltha.svc.cluster.local
        voltha_port: 8882
        voltha_user: voltha
        voltha_pass: admin
        
        # Informations on how to reach ONOS-VOLTHA
        onos_voltha_url: onos-voltha-ui.voltha.svc.cluster.local
        onos_voltha_port: 8181
        onos_voltha_user: karaf
        onos_voltha_pass: karaf
        
        # Which kind of policy is applied when a new ONU is discovered
        onu_provisioning: allow_all [deny_all, custom_logic]
``` 

## ONU Porvisioning policies

### Allow all

This means that any discovered onu is activated and the POD is configured to enable dataplane traffic for this user

### Deny all

ONU discovery events are ignored, the operator will manually need to push the subscriber configuration

### Custom Logic

Whenever a more complex logic is required this is delegated to an extenal service, from now on referenced as `MyOssService`.
We assume that:
- the  `vOLTService` service is a subscriber of `MyOssService` via `ServiceDependency`
- `MyOssService` has `type = oss`
- `MyOssService` expose and API named `validate_onu`
    - the `validate_onu` API will be responsible to create a subscriber in XOS