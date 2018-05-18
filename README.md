# vOLT 

This repositoritory contains the XOS service that is responsible for the integration with VOLTHA.

At the moment the `RCORDService` assume that this service (or a service exposing the same APIs) is sitting after it in the service chain. 

## ONU activation discovery

This service will listen for events on the kafka bus, in the topic `onu.events`

The events this service will react to are:
- onu activated

### ONU Activation policy

We assume that:
- the  `vOLTService` service is a subscriber of `MyOssService` via `ServiceDependency`
- `MyOssService` has `type = oss`
- `MyOssService` expose and API named `validate_onu`
    - the `validate_onu` API will be responsible to create a subscriber in XOS
    
If no OSS Service is found in between the providers of `vOLTService` no action is taken as a consequence of an event.
