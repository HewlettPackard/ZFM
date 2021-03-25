#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

switch_attributes = """
{
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.LPRT.{CIDS}.RouteSet": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/LPRT/{CIDS}/RouteSet",
        "@odata.type": "#RouteSetCollection.RouteSetCollection",
        "Name": "Gen-Z Fabric Port {SWITCH_PORTS} Linear Packet Relay Table Entry Route Set Collection",
        "Members@odata.count": "{ROUTES}",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/LPRT/{CIDS}/RouteSet/{ROUTES}"
            }
        ]
    },
    "redfish.v1.UpdateService.FirmwareInventory.MFW": {
        "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/MFW",
        "@odata.type": "#SoftwareInventory.v1_1_1.SoftwareInventory",
        "Description": "Contents: Management Firmware",
        "Id": "MFW",
        "Name": "Management Firmware",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "Updateable": false,
        "Version": "<MFW Version>"
    },
    "redfish.v1.TelemetryService": {
        "@odata.id": "/redfish/v1/TelemetryService",
        "@odata.type": "#TelemetryService.v1_1_0.TelemetryService",
        "Name": "Telemetry Service",
        "Description": "Telemetry Service",
        "Id": "TelemetryService",
        "Oem": {
            "Hpe": {
                "ServiceEnabled": true,
                "BrokerIp": "1.1.1.1",
                "FrequencyHz": 2,
                "Devices": [
                    {
                        "DeviceEnabled": false,
                        "Type": "Switch",
                        "UID": 124,
                        "NumPorts": 60,
                        "RegisterSet": [
                            {
                                "Register": "GenZ_Common_0x00",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x08",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x10",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x18",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x20",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x28",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x30",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x38",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x50",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x58",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x60",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x68",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x70",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x78",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x80",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x88",
                                "RegisterEnabled": false
                            }
                        ]
                    },
                    {
                        "DeviceEnabled": false,
                        "Type": "Switch",
                        "UID": 125,
                        "NumPorts": 60,
                        "RegisterSet": [
                            {
                                "Register": "GenZ_Common_0x00",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x08",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x10",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x18",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x20",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x28",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x30",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_Common_0x38",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x50",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x58",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x60",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x68",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x70",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x78",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x80",
                                "RegisterEnabled": false
                            },
                            {
                                "Register": "GenZ_ReqResp_0x88",
                                "RegisterEnabled": false
                            }
                        ]
                    }
                ]
            }
        }
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.LPRT": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/LPRT",
        "@odata.type": "#RouteCollection.RouteCollection",
        "Name": "Gen-Z Fabric Port {SWITCH_PORTS} Linear Packet Relay Table",
        "Members@odata.count": "{CIDS}",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/LPRT/{CIDS}"
            }
        ]
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.VCAT": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/VCAT",
        "@odata.type": "#VCATCollection.VCATCollection",
        "Name": "VCAT Collection",
        "Description": "Gen-Z Port {SWITCH_PORTS} Virtual Channel Action Table Collection",
        "Members@odata.count": "{VCS}",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/VCAT/{VCS}"
            }
        ]
    },
    "redfish.v1.Fabrics.GenZ": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ",
        "@odata.type": "#Fabric.v1_0_0.Fabric",
        "Id": "GenZ",
        "Name": "Gen-Z Fabric",
        "FabricType": "GenZ",
        "Description": "A Gen-Z Fabric Switch",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "Switches": {
            "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches"
        },
        "Endpoints": {
            "@odata.id": "/redfish/v1/Fabrics/GenZ/Endpoints"
        }
    },
    "redfish.v1.Managers": {
        "@odata.id": "/redfish/v1/Managers",
        "@odata.type": "#ManagerCollection.ManagerCollection",
        "Name": "Managers",
        "Members@odata.count": 1,
        "Description": "Managers view",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Managers/1"
            }
        ]
    },
    "redfish.v1.Managers.1.EthernetInterfaces.1": {
        "@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces/1",
        "@odata.type": "#EthernetInterface.v1_4_0.EthernetInterface",
        "Description": "Configuration of this Manager Network Interface",
        "HostName": "<fill this in>",
        "FQDN": "<fill this in>",
        "FullDuplex": true,
        "AutoNeg": true,
        "IPv4Addresses": [
            {
                "Address": "0.0.0.0",
                "AddressOrigin": "DHCP",
                "Gateway": "0.0.0.0",
                "SubnetMask": "0.0.0.0"
            }
        ],
        "Id": "1",
        "MACAddress": "FC:15:B4:97:36:8E",
        "SpeedMbps": 1000,
        "Name": "Manager Dedicated Network Interface",
        "NameServers": [
            "0.0.0.0",
            "0.0.0.0"
        ],
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        }
    },
    "redfish.v1.UpdateService.FirmwareInventory": {
        "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory",
        "@odata.type": "#SoftwareInventoryCollection.SoftwareInventoryCollection",
        "Name": "Firmware Inventory Collection",
        "Members@odata.count": 5,
        "Members": [
            {
                "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/MPOS"
            },
            {
                "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/MFW"
            },
            {
                "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/Drivers"
            },
            {
                "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/FWImage"
            },
            {
                "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/MHW_FPGA"
            }
        ]
    },
    "redfish.v1": {
        "@odata.type": "#ServiceRoot.v1_3_1.ServiceRoot",
        "@odata.id": "/redfish/v1",
        "Id": "RootService",
        "Name": "Platoon System Root Service",
        "Description": "This is a goal-version model of Redfish, not representative of a particular release.",
        "RedfishVersion": "1.6.0",
        "UUID": "1ad59fe9-49f9-52fa-9a93-e349f9477fe0",
        "Fabrics": {
            "@odata.id": "/redfish/v1/Fabrics"
        },
        "Managers": {
            "@odata.id": "/redfish/v1/Managers"
        },
        "Chassis": {
            "@odata.id": "/redfish/v1/Chassis"
        },
        "TelemetryService": {
            "@odata.id": "/redfish/v1/TelemetryService"
        },
        "UpdateService": {
            "@odata.id": "/redfish/v1/UpdateService"
        }
    },
    "redfish.v1.Fabrics": {
        "@odata.id": "/redfish/v1/Fabrics",
        "@odata.type": "#FabricCollection.FabricCollection",
        "Name": "Fabric Collection",
        "Members.odata.count": 1,
        "Members": [
            {
                "@odata.id": "/redfish/v1/Fabrics/GenZ"
            }
        ]
    },
    "redfish.v1.Chassis": {
        "@odata.type": "#ChassisCollection.ChassisCollection",
        "@odata.id": "/redfish/v1/Chassis",
        "Name": "Chassis Collection",
        "Members@odata.count": 1,
        "Members": [
            {
                "@odata.id": "/redfish/v1/Chassis/1"
            }
        ]
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.VCAT.{VCS}": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/VCAT/{VCS}",
        "@odata.type": "#VCATEntry.v1_0_0.VCATEntry",
        "Id": "{VCS}",
        "Name": "VCAT Entry {VCS}",
        "Description": "Gen-Z Port {SWITCH_PORTS} Virtual Channel Action Table Entry {VCS}",
        "RawEntryHex": "0x123456",
        "VCATEntry": []
    },
    "redfish.v1.Managers.1.EthernetInterfaces": {
        "@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces",
        "@odata.type": "#EthernetInterfaceCollection.EthernetInterfaceCollection",
        "Name": "Manager Network Interfaces",
        "Description": "Configuration of Manager Network Interfaces",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces/1"
            }
        ],
        "Members@odata.count": 1
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}",
        "@odata.type": "#Switch.v1_0_0.Switch",
        "Id": "Switch{SWITCHES}",
        "Name": "Gen-Z Switch",
        "SwitchType": "GenZ",
        "Manufacturer": "HPE",
        "Model": "AlphaStar",
        "SerialNumber": "2M220100SL",
        "Ports": {
            "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports"
        },
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "Links": {
            "Endpoints": [
                {
                    "@odata.id": "/redfish/v1/Fabrics/GenZ/Endpoints/{SWITCHES}"
                }
            ]
        },
        "Oem": {
            "Hpe": {
                "Location": {
                    "ComponentID": 1
                }
            }
        }
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.LPRT.{CIDS}": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/LPRT/{CIDS}",
        "@odata.type": "#RouteEntry.v1_0_0.RouteEntry",
        "Id": "{CIDS}",
        "Name": "LPRT{CIDS}",
        "Description": "Gen-Z Port {SWITCH_PORTS} LPRT Entry {CIDS}",
        "RawEntryHex": "0x34EF124500000000",
        "RouteSet": {
            "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/LPRT/{CIDS}/RouteSet"
        },
        "MinimumHopCount": 1
    },
    "redfish.v1.Managers.1.NetworkProtocol": {
        "@odata.id": "/redfish/v1/Managers/1/NetworkProtocol",
        "@odata.type": "#ManagerNetworkProtocol.v1_2_0.ManagerNetworkProtocol",
        "Name": "Manager Network Services",
        "Id": "NetworkProtocol",
        "Description": "Network Protocol Services",
        "HostName": "<fill this in>",
        "FQDN": "<fill this in>",
        "HTTP": {
            "Port": 80,
            "ProtocolEnabled": true
        },
        "Links": {
            "EthernetInterfaces": {
                "@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces"
            }
        },
        "SSH": {
            "Port": 22,
            "ProtocolEnabled": true
        },
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        }
    },
    "redfish.v1.UpdateService.FirmwareInventory.MHW_FPGA": {
        "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/MHW_FPGA",
        "@odata.type": "#SoftwareInventory.v1_1_1.SoftwareInventory",
        "Description": "Contents: Management Subsystem FPGA",
        "Id": "MHW",
        "Name": "Management Hardware FPGA",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "Updateable": false,
        "Version": "<MHW Version>"
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.MPRT": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/MPRT",
        "@odata.type": "#RouteCollection.RouteCollection",
        "Name": "Gen-Z Fabric Port {SWITCH_PORTS} Multi-Subnet Packet Relay Table",
        "Members@odata.count": "{SIDS}",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/MPRT/{SIDS}"
            }
        ]
    },
    "redfish.v1.UpdateService": {
        "@odata.type": "#UpdateService.v1_1_0.UpdateService",
        "@odata.id": "/redfish/v1/UpdateService",
        "Name": "Update Service",
        "Description": "Platoon Switch Update Service",
        "Id": "UpdateService",
        "ServiceEnabled": false,
        "FirmwareInventory": {
            "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory"
        }
    },
    "redfish.v1.Managers.1": {
        "@odata.id": "/redfish/v1/Managers/1",
        "@odata.type": "#Manager.v1_3_3.Manager",
        "Id": "1",
        "Name": "Switch Node Manager",
        "ManagerType": "MP",
        "Description": "Platoon Switch",
        "Actions": {
            "#Manager.Reset": {
                "target": "/redfish/v1/Managers/1/Actions/Manager.Reset",
                "ResetType@Redfish.AllowableValues": [
                    "GracefulRestart",
                    "ForceRestart"
                ]
            }
        },
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "CommandShell": {
            "ServiceEnabled": true,
            "MaxConcurrentSessions": 9,
            "ConnectTypesSupported": [
                "SSH"
            ]
        },
        "EthernetInterfaces": {
            "@odata.id": "/redfish/v1/Managers/1/EthernetInterfaces"
        },
        "FirmwareVersion": "<MFW Version>",
        "Links": {
            "ManagerForChassis": [
                {
                    "@odata.id": "/redfish/v1/Chassis/1"
                }
            ],
            "ManagerInChassis": {
                "@odata.id": "/redfish/v1/Chassis/1"
            }
        },
        "NetworkProtocol": {
            "@odata.id": "/redfish/v1/Managers/1/NetworkProtocol"
        },
        "Oem": {
            "Hpe": {
                "FrontPanelUSB": {
                    "State": "Ready"
                },
                "IdleConnectionTimeoutMinutes": 30,
                "SerialCLISpeed": 9600,
                "SerialCLIStatus": "Enabled"
            }
        }
    },
    "redfish.v1.UpdateService.FirmwareInventory.FWImage": {
        "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/FWImage",
        "@odata.type": "#SoftwareInventory.v1_1_1.SoftwareInventory",
        "Description": "Contents: Image of FW Components",
        "Id": "FWImage",
        "Name": "Firmware Image",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "Updateable": false,
        "Version": "<FWImage Version>"
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.MPRT.{SIDS}.RouteSet": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/MPRT/{SIDS}/RouteSet",
        "@odata.type": "#RouteSetCollection.RouteSetCollection",
        "Name": "Gen-Z Fabric Port {SWITCH_PORTS} MultiSubnet Packet Relay Table Entry Route Set Collection",
        "Members@odata.count": "{ROUTES}",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/MPRT/{SIDS}/RouteSet/{ROUTES}"
            }
        ]
    },
    "redfish.v1.UpdateService.FirmwareInventory.MPOS": {
        "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/MPOS",
        "@odata.type": "#SoftwareInventory.v1_1_1.SoftwareInventory",
        "Description": "Contents: Management Processor Operating System",
        "Id": "MPOS",
        "Name": "Management Processor OS",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "Updateable": false,
        "Version": "<MPOS Version>"
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.MPRT.{SIDS}.RouteSet.{ROUTES}": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/MPRT/{SIDS}/RouteSet/{ROUTES}",
        "@odata.type": "#RouteSetEntry.v1_0_0.RouteSetEntry",
        "Id": "{ROUTES}",
        "Name": "Route{ROUTES}",
        "Description": "Gen-Z Port {SWITCH_PORTS} MPRT Entry {SIDS} Route {ROUTES}",
        "Valid": false,
        "VCAction": 0,
        "HopCount": 0,
        "EgressIdentifier": 0
    },
    "redfish.v1.UpdateService.FirmwareInventory.Drivers": {
        "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/Drivers",
        "@odata.type": "#SoftwareInventory.v1_1_1.SoftwareInventory",
        "Description": "Contents: MP OS Drivers",
        "Id": "Drivers",
        "Name": "Drivers",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "Updateable": false,
        "Version": "<Drivers Version>"
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}",
        "@odata.type": "#Port.v1_1_0.Port",
        "Id": "{SWITCH_PORTS}",
        "Name": "Gen-Z Port {SWITCH_PORTS}",
        "Description": "Gen-Z Port {SWITCH_PORTS}",
        "PortProtocol": "GenZ",
        "PortType": "BidirectionalPort",
        "PortMedium": "Optical",
        "CurrentSpeedGbps": 56,
        "Width": 4,
        "MaxSpeedGbps": 56,
        "LinkState": "Disabled",
        "InterfaceState": "Disabled",
        "Status": {
            "State": "Disabled",
            "Health": "OK"
        },
        "Gen-Z": {
            "LPRT": {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/LPRT"
            },
            "MPRT": {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/MPRT"
            },
            "VCAT": {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/VCAT"
            }
        },
        "Metrics": {
            "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/Metrics"
        },
        "Oem": {
            "Hpe": {
                "RemoteComponentID": {
                    "UID": 0,
                    "Port": 0
                }
            }
        }
    },
    "redfish.v1.Fabrics.GenZ.Endpoints": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Endpoints",
        "@odata.type": "#EndpointCollection.EndpointCollection",
        "Name": "Gen-Z Endpoint Collection",
        "Members@odata.count": "{ENDPOINTS}",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Endpoints/{ENDPOINTS}"
            }
        ]
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.MPRT.{SIDS}": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/MPRT/{SIDS}",
        "@odata.type": "#RouteEntry.v1_0_0.RouteEntry",
        "Id": "{SIDS}",
        "Name": "MPRT{SIDS}",
        "Description": "Gen-Z Port {SWITCH_PORTS} MPRT Entry {SIDS}",
        "RawEntryHex": "0x34EF124500000000",
        "RouteSet": {
            "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/MPRT/{SIDS}/RouteSet"
        },
        "MinimumHopCount": 1
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports",
        "@odata.type": "#PortCollection.PortCollection",
        "Name": "Gen-Z Port Collection",
        "Members@odata.count": "{SWITCH_PORTS}",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}"
            }
        ]
    },
    "redfish.v1.Fabrics.GenZ.Endpoints.{ENDPOINTS}": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Endpoints/{ENDPOINTS}",
        "@odata.type": "#Endpoint.v1_2_0.Endpoint",
        "Id": "{ENDPOINTS}",
        "Name": "Local Switch",
        "Description": "Local Switch Control Space",
        "EndpointProtocol": "GenZ",
        "ConnectedEntities": [
            {
                "EntityType": "Switch",
                "EntityRole": "Target",
                "GCID": {
                    "ComponentID": 0,
                    "SubnetID": 0
                },
                "EntityLink": {
                    "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{ENDPOINTS}"
                }
            }
        ],
        "Oem": {
            "Hpe": {
                "UID": 0,
                "Location": {
                    "ComponentID": 1
                }
            }
        }
    },
    "redfish.v1.Fabrics.GenZ.Switches": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches",
        "@odata.type": "#SwitchCollection.SwitchCollection",
        "Name": "Switch Collection",
        "Members@odata.count": "{SWITCHES}",
        "Members": [
            {
                "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}"
            }
        ]
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.LPRT.{CIDS}.RouteSet.{ROUTES}": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/LPRT/{CIDS}/RouteSet/{ROUTES}",
        "@odata.type": "#RouteSetEntry.v1_0_0.RouteSetEntry",
        "Id": "{ROUTES}",
        "Name": "Route{ROUTES}",
        "Description": "Gen-Z Port {SWITCH_PORTS} LPRT Entry {CIDS} Route {ROUTES}",
        "Valid": false,
        "VCAction": 0,
        "HopCount": 0,
        "EgressIdentifier": 0
    },
    "redfish.v1.Fabrics.GenZ.Switches.Switch{SWITCHES}.Ports.{SWITCH_PORTS}.Metrics": {
        "@odata.id": "/redfish/v1/Fabrics/GenZ/Switches/Switch{SWITCHES}/Ports/{SWITCH_PORTS}/Metrics",
        "@odata.type": "#PortMetrics.v1_0_0.PortMetrics",
        "Id": "Metrics",
        "Name": "Gen-Z Port {SWITCH_PORTS} Metrics",
        "Description": "Gen-Z Port {SWITCH_PORTS} Metrics",
        "TimeStamp": "2017-11-23T17:17:42-0600",
        "Gen-Z": {
            "PCRCErrors": 0,
            "ECRCErrors": 0,
            "TXStompedECRC": 0,
            "RXStompedECRC": 0,
            "NonCRCTransientErrors": 0,
            "LLRRecovery": 0,
            "PacketDeadlineDiscards": 0,
            "MarkedECN": 0,
            "ReceivedECN": 0,
            "LinkNTE": 0,
            "AKEYViolations": 0,
            "TotalTransReqs": 0,
            "TotalTransReqBytes": 0,
            "TotalRecvReqs": 0,
            "TotalRecvReqBytes": 0,
            "TotalTransResps": 0,
            "TotalTransRespBytes": 0,
            "TotalRecvResps": 0,
            "TotalRecvRespBytes": 0
        },
        "Oem": {
            "Hpe": {
                "Metrics": {
                    "VC0": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC1": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC2": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC3": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC4": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC5": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC6": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC7": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC8": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC9": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC10": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC11": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC12": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC13": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC14": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    },
                    "VC15": {
                        "Occupancy": 0,
                        "RecvBytes": 0,
                        "RecvCount": 0,
                        "XmitBytes": 0,
                        "XmitCount": 0
                    }
                }
            }
        }
    },
    "redfish.v1.Chassis.1": {
        "@odata.type": "#Chassis.v1_6_0.Chassis",
        "@odata.id": "/redfish/v1/Chassis/1",
        "Id": "1",
        "Name": "Platoon Switch",
        "Manufacturer": "HPE",
        "Model": "Platoon",
        "SerialNumber": "<SerialNumber>",
        "PowerState": "On",
        "IndicatorLED": "Lit",
        "ChassisType": "Sled",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "Links": {
            "ManagedBy": [
                {
                    "@odata.id": "/redfish/v1/Managers/1"
                }
            ],
            "ManagersInChassis": [
                {
                    "@odata.id": "/redfish/v1/Managers/1"
                }
            ]
        },
        "Actions": {
            "#Chassis.Reset": {
                "target": "/redfish/v1/Chassis/1/Actions/Chassis.Reset",
                "ResetType@Redfish.AllowableValues": [
                    "On",
                    "ForceOff",
                    "PushPowerButton",
                    "PowerCycle"
                ]
            }
        },
        "Oem": {
            "Hpe": {
                "NodeType": "Switch",
                "Location": {
                    "RackID": 0,
                    "ChassisID": 0,
                    "SlotID": 0,
                    "NodeID": 0
                }
            }
        }
    }
}
"""
