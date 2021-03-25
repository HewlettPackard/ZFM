#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import sys
from km.routers.NxM import NxM


class VDAL(NxM):
    def __init__(self, fabric, parameters, vc_map):
        self.num_dimensions = fabric.get_dimensions()

        #
        # Routing state machine.  See NxM.route_switch_to_switch() for documentation on format.
        #
        self.state_machine = {
            # -------------------------------------------------------------------------------------------------------------------
            ('XY', 'L') : { 'EXIT'      : [0,1,2,3]                                                                            },
            ('Xy', 'L') : {                                                   'Y_DIRECT'  : [0,1,2,3], 'Y_DEROUTE' : [0,1,2,3] },
            ('xY', 'L') : { 'X_DIRECT'  : [0,1,2,3], 'X_DEROUTE' : [0,1,2,3]                                                   },
            ('xy', 'L') : { 'X_DIRECT'  : [0,1,2,3], 'X_DEROUTE' : [0,1,2,3], 'Y_DIRECT'  : [0,1,2,3], 'Y_DEROUTE' : [0,1,2,3] },
            # -------------------------------------------------------------------------------------------------------------------
            ('XY', 'X') : { 'EXIT'      : [0,1,2,3]                                                                            },
            ('Xy', 'X') : {                                                   'Y_DIRECT'  : [0,1,2],   'Y_DEROUTE' : [0,1]     },
            ('xY', 'X') : { 'X_DIRECT'  : [1,2]                                                                                },
            ('xy', 'X') : { 'X_DIRECT'  : [0,1],                              'Y_DIRECT'  : [0,1],     'Y_DEROUTE' : [0]       },
            # -------------------------------------------------------------------------------------------------------------------
            ('XY', 'Y') : { 'EXIT'      : [0,1,2,3]                                                                            },
            ('Xy', 'Y') : {                                                   'Y_DIRECT'  : [1,2]                              },
            ('xY', 'Y') : { 'X_DIRECT'  : [0,1,2],   'X_DEROUTE' : [0,1]                                                       },
            ('xy', 'Y') : { 'X_DIRECT'  : [0,1],     'X_DEROUTE' : [0],       'Y_DIRECT'  : [0,1]                              },
            # -------------------------------------------------------------------------------------------------------------------
        }

        #
        # Setup the VCATs, etc
        #
        super().__init__('VDAL', parameters, vc_map)


    def get_threshold(self, port_type, route_type, rc):
        if 'DEROUTE' not in route_type:
            threshold = 7
        elif port_type == 'L':
            threshold = 2*self.num_dimensions
        else:
            threshold = max(0, 2*self.num_dimensions - rc)

        return threshold


    def get_mask(self, location, port_type, route_type, rc, rc_mask):
        if location == 'XY':                        # destination switch, use configured egress RCs
            mask = rc_mask[self.egress_rc_type]
        elif port_type == 'L':                      # originating switch, use configured ingress RCs
            mask = rc_mask[self.ingress_rc_type]
        else:                                       # increment the RC for normal traffic
            mask = rc_mask[rc+1]

        return mask

# ----------------------------------------------------------------------------------------------------------------------

    """
    Another view of the state machine.  This view rearranges the rows to group them by location first.


            # -------------------------------------------------------------------------------------------------------------------
            ('XY', 'L') : { 'EXIT'      : [0,1,2,3]                                                                            },
            ('XY', 'X') : { 'EXIT'      : [0,1,2,3]                                                                            },
            ('XY', 'Y') : { 'EXIT'      : [0,1,2,3]                                                                            },
            # -------------------------------------------------------------------------------------------------------------------
            ('Xy', 'L') : {                                                   'Y_DIRECT'  : [0,1,2,3], 'Y_DEROUTE' : [0,1,2,3] },
            ('Xy', 'X') : {                                                   'Y_DIRECT'  : [0,1,2],   'Y_DEROUTE' : [0,1]     },
            ('Xy', 'Y') : {                                                   'Y_DIRECT'  : [1,2]                              },
            # -------------------------------------------------------------------------------------------------------------------
            ('xY', 'L') : { 'X_DIRECT'  : [0,1,2,3], 'X_DEROUTE' : [0,1,2,3]                                                   },
            ('xY', 'X') : { 'X_DIRECT'  : [1,2]                                                                                },
            ('xY', 'Y') : { 'X_DIRECT'  : [0,1,2],   'X_DEROUTE' : [0,1]                                                       },
            # -------------------------------------------------------------------------------------------------------------------
            ('xy', 'L') : { 'X_DIRECT'  : [0,1,2,3], 'X_DEROUTE' : [0,1,2,3], 'Y_DIRECT'  : [0,1,2,3], 'Y_DEROUTE' : [0,1,2,3] },
            ('xy', 'X') : { 'X_DIRECT'  : [0,1],                              'Y_DIRECT'  : [0,1],     'Y_DEROUTE' : [0]       },
            ('xy', 'Y') : { 'X_DIRECT'  : [0,1],     'X_DEROUTE' : [0],       'Y_DIRECT'  : [0,1]                              },
            # -------------------------------------------------------------------------------------------------------------------

    """
