# vOLT Service

The `vOLT Service` is responsible for configuring and managing access networks (OLT and ONU devices and the associated PON network) and does so by leveraging `VOLTHA`.

## Models

Below is a diagram describing the models that comprise this service,
followed by a brief description of them.
For a full reference on these models, please take a look at their
[xProto](https://github.com/opencord/olt-service/blob/master/xos/synchronizer/models/volt.xproto)
representation.

![ER Diagram](static/vOLTService_ER_diagram.png)

- `VOLTService`. Contains information that the synchronizer needs to access `VOLTHA` and `ONOS-VOLTHA`
    - `voltha_url`, `voltha_port`. Hostname and port of VOLTHA-API gRPC endpoint.
- `vOLTServiceInstance`. Extends `ServiceInstance`, and holds the OLT subscriber-related state for the service chain.
    - `description`. Description of the service instance.
    - `onu_device`. Relation to an ONUDevice object.
- `OLTDevice`. Represents an OLT Device. Contains the information needed to pre-provision and activate the OLT.
    - `volt_service`. Relation to the VOLTService that owns this OLT.
    - `name`. Name of device.
    - `device_type`. Type of device, defaults to `openolt`.
    - `host`, `port`. Hostname and port of OLT.
    - `mac_address`. MAC Address of OLT.
    - `serial_number`. Serial number of OLT.
    - `device_id`. VOLTHA device id.
    - `admin_state`. [`ENABLED` | `DISABLED`]. Administrative state, pushed to device.
    - `oper_status`. Operational status, learned from device.
    - `of_id`. Openflow ID.
    - `dp_id`. Datapath ID.
    - `uplink`. Uplink port. Exposed via sadis.
    - `driver`. Driver, defaults to `voltha`. Deprecated.
    - `switch_datapath_id`, `switch_port`. Identifies the switch the OLT is attached to.
    - `outer_tpid`. Outer VLAN id field EtherType.
    - `nas_id`. Authentication ID (propagated to the free-radius server via sadis)
    - `technology`. [`gpon` | `xgspon`]. Technology being utilized by the adapter.
- `ONUDevice`. Represents an ONU Device.
    - `pon_port`. Relation to a PONPort that connects this ONU to an OLT.
    - `serial_number`. Serial number of the ONU.
    - `vendor`. Vendor of the ONU.
    - `device_type`. Device type, defaults to `asfvolt16_olt`.
    - `device_id`. VOLTHA device id.
    - `admin_state`. [`ENABLED` | `DISABLED` | `ADMIN_DISABLED`]. Administrative state, pushed to device. `ADMIN_DISABLED` is intended to be used by an operator to manually disable an ONU and that value will persist until changed by the operator. `DISABLED` and `ENABLED` are typically managed by a workflow driver and may change state based on events from Voltha.
    - `oper_status`. Operational status, learned from device.
    - `connect_status`. Whether port is active.
    - `reason`. ONU device configuration state machine status message.
- `NNIPort`, `PONPort`, `ANIPort`, `UNIPort`. These represent various ports attached to OLTs and ONUs.
- `TechnologyProfile`. Contains PON related information, see [Technology Profile Management](https://github.com/opencord/voltha/tree/master/common/tech_profile) in the VOLTHA repo.

## Example Tosca

These are examples are taken from the olt-service repository. See the
[samples](https://github.com/opencord/olt-service/tree/master/samples) folder for additional examples.

### Create an OLT

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
imports:
  - custom_types/oltdevice.yaml
  - custom_types/voltservice.yaml
description: Create a simulated OLT Device in VOLTHA
topology_template:
  node_templates:

    service#volt:
      type: tosca.nodes.VOLTService
      properties:
        name: volt
        must-exist: true

    device#olt:
      type: tosca.nodes.OLTDevice
      properties:
        name: test_olt
        device_type: ponsim
        host: 172.17.0.1
        port: 50060
        switch_datapath_id: of:0000000000000001
        switch_port: "1"
        outer_tpid: "0x8100"
        dp_id: of:0000000ce2314000
        uplink: "129"
      requirements:
        - volt_service:
            node: service#volt
            relationship: tosca.relationships.BelongsToOne
```

### Add a PONPort and ONUDevice to an OLT

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
imports:
  - custom_types/oltdevice.yaml
  - custom_types/onudevice.yaml
  - custom_types/ponport.yaml
  - custom_types/voltservice.yaml
  - custom_types/uniport.yaml
description: Create a simulated OLT Device in VOLTHA
topology_template:
  node_templates:

    device#olt:
      type: tosca.nodes.OLTDevice
      properties:
        name: test_olt
        must-exist: true

    pon_port:
      type: tosca.nodes.PONPort
      properties:
        name: test_pon_port_1
        port_no: 2
      requirements:
        - olt_device:
            node: device#olt
            relationship: tosca.relationships.BelongsToOne

    device#onu:
      type: tosca.nodes.ONUDevice
      properties:
        serial_number: BRCM1234
        vendor: Broadcom
      requirements:
        - pon_port:
            node: pon_port
            relationship: tosca.relationships.BelongsToOne

    uni_port:
      type: tosca.nodes.UNIPort
      properties:
        name: test_uni_port_1
        port_no: 2
      requirements:
        - onu_device:
            node: device#onu
            relationship: tosca.relationships.BelongsToOne
```

## Create a Technology Profile

This example uses 4 Gem ports:

```yaml
tosca_definitions_version: tosca_simple_yaml_1_0
imports:
  - custom_types/technologyprofile.yaml
description: Create a TechnologyProfile to configure the PON in VOLTHA
topology_template:
  node_templates:

    technologyProfile:
      type: tosca.nodes.TechnologyProfile
      properties:
        profile_id: 64
        technology: xgspon
        profile_value: >
          {
            "name": "4QueueHybridProfileMap1",
            "profile_type": "XPON",
            "version": 1,
            "num_gem_ports": 4,
            "instance_control": {
              "onu": "multi-instance",
              "uni": "single-instance",
              "max_gem_payload_size": "auto"
            },
            "us_scheduler": {
              "additional_bw": "auto",
              "direction": "UPSTREAM",
              "priority": 0,
              "weight": 0,
              "q_sched_policy": "hybrid"
            },
            "ds_scheduler": {
              "additional_bw": "auto",
              "direction": "DOWNSTREAM",
              "priority": 0,
              "weight": 0,
              "q_sched_policy": "hybrid"
            },
            "upstream_gem_port_attribute_list": [
              {
                "pbit_map": "0b00000101",
                "aes_encryption": "True",
                "scheduling_policy": "WRR",
                "priority_q": 4,
                "weight": 25,
                "discard_policy": "TailDrop",
                "max_q_size": "auto",
                "discard_config": {
                  "max_threshold": 0,
                  "min_threshold": 0,
                  "max_probability": 0
                }
              },
              {
                "pbit_map": "0b00011010",
                "aes_encryption": "True",
                "scheduling_policy": "WRR",
                "priority_q": 3,
                "weight": 75,
                "discard_policy": "TailDrop",
                "max_q_size": "auto",
                "discard_config": {
                  "min_threshold": 0,
                  "max_threshold": 0,
                  "max_probability": 0
                }
              },
              {
                "pbit_map": "0b00100000",
                "aes_encryption": "True",
                "scheduling_policy": "StrictPriority",
                "priority_q": 2,
                "weight": 0,
                "discard_policy": "TailDrop",
                "max_q_size": "auto",
                "discard_config": {
                  "min_threshold": 0,
                  "max_threshold": 0,
                  "max_probability": 0
                }
              },
              {
                "pbit_map": "0b11000000",
                "aes_encryption": "True",
                "scheduling_policy": "StrictPriority",
                "priority_q": 1,
                "weight": 25,
                "discard_policy": "TailDrop",
                "max_q_size": "auto",
                "discard_config": {
                  "min_threshold": 0,
                  "max_threshold": 0,
                  "max_probability": 0
                }
              }
            ],
            "downstream_gem_port_attribute_list": [
              {
                "pbit_map": "0b00000101",
                "aes_encryption": "True",
                "scheduling_policy": "WRR",
                "priority_q": 4,
                "weight": 10,
                "discard_policy": "TailDrop",
                "max_q_size": "auto",
                "discard_config": {
                  "min_threshold": 0,
                  "max_threshold": 0,
                  "max_probability": 0
                }
              },
              {
                "pbit_map": "0b00011010",
                "aes_encryption": "True",
                "scheduling_policy": "WRR",
                "priority_q": 3,
                "weight": 90,
                "discard_policy": "TailDrop",
                "max_q_size": "auto",
                "discard_config": {
                  "min_threshold": 0,
                  "max_threshold": 0,
                  "max_probability": 0
                }
              },
              {
                "pbit_map": "0b00100000",
                "aes_encryption": "True",
                "scheduling_policy": "StrictPriority",
                "priority_q": 2,
                "weight": 0,
                "discard_policy": "TailDrop",
                "max_q_size": "auto",
                "discard_config": {
                  "min_threshold": 0,
                  "max_threshold": 0,
                  "max_probability": 0
                }
              },
              {
                "pbit_map": "0b11000000",
                "aes_encryption": "True",
                "scheduling_policy": "StrictPriority",
                "priority_q": 1,
                "weight": 25,
                "discard_policy": "TailDrop",
                "max_q_size": "auto",
                "discard_config": {
                  "min_threshold": 0,
                  "max_threshold": 0,
                  "max_probability": 0
                }
              }
            ]
          }
```

## Integration with other Services

The western neighbor of the vOLT Service is typically the R-CORD Service, which handles subscriber-related state. The vOLT Service may pull subscriber related information, such as VLAN tags, ONU serial numbers, etc., from that service.

The eastern neighbor of the vOLT Service is typically the Fabric Crossconnect Service, which programs the aggregation switch to connect OLT traffic to the Internet. When a `VOLTServiceInstance` is created, the vOLT Service will create a `ServiceInstance` in its eastern neighbor to connect this traffic.

## Synchronization Workflow

### Push steps

There are four top-down steps in this service:

- `SyncOLTDevice` to pre-provision and enable OLT devices. Also handles disabling and deleting the OLT from `VOLTHA` when the model is deleted in XOS.
- `SyncONUDevice` to admin enable/disable an ONU Device (or to configure one if they're not discovered by the OLT software)
- `SyncVOLTServiceInstance` to add the subscriber in `ONOS-VOLTHA`
- `SyncTechnologyProfile` to push the Technology Profile into ETCD

### Pull steps

The vOLT synchronizer is currently pulling `OLTDevice`, `PONPort`, `NNIPort` and
`ONUDevices` from `VOLTHA`. When these devices are created in VOLTHA, the corresponding objects will automatically be created in the XOS data model.

### Event steps

The vOLT synchronizer is listening over the kafka bus for events in the `xos.kubernetes.pod-details` topic. These events are used to automatically re-push state to VOLTHA when VOLTHA containers are restarted.

### Model Policies

The `VOLTServiceInstance` model policy will create an eastbound service instance. This is typically in a fabric-related service, such as the Fabric Crossconnect Service, and is responsible for connecting OLT/ONU traffic to the Internet. The model policy will leverage an `acquire_service_instance()` method in the eastbound service to create the eastbound service instance.
