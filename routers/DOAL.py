#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

import sys
from km.routers.NxM import NxM


class DOAL(NxM):
    def __init__(self, fabric, parameters, vc_map):
        order_flag = parameters.get('XDimensionFirst', True)
        self.dim1,self.dim2  = ('X','Y') if order_flag else ('Y','X')

        #
        # Routing state machine.  See NxM.route_switch_to_switch() for documentation on format.
        #
        if self.dim1 == 'X':
            self.state_machine = {
                # --------------------------------------------------------
                ('XY', 'L') : { 'EXIT'     : [0,1]                      },
                ('Xy', 'L') : { 'Y_DIRECT' : [0,1], 'Y_DEROUTE' : [0,1] },
                ('xY', 'L') : { 'X_DIRECT' : [0,1], 'X_DEROUTE' : [0,1] },
                ('xy', 'L') : { 'X_DIRECT' : [0,1], 'X_DEROUTE' : [0,1] },
                # --------------------------------------------------------
                ('XY', 'X') : { 'EXIT'     : [0,1]                      },
                ('Xy', 'X') : { 'Y_DIRECT' : [0,1], 'Y_DEROUTE' : [0,1] },
                ('xY', 'X') : { 'X_FINISH' : [1]                        },
                ('xy', 'X') : { 'X_FINISH' : [1]                        },
                # --------------------------------------------------------
                ('XY', 'Y') : { 'EXIT'     : [0,1]                      },
                ('Xy', 'Y') : { 'Y_FINISH' : [1]                        },
                ('xY', 'Y') : {                                         },
                ('xy', 'Y') : {                                         },
                # --------------------------------------------------------
            }
        else:
            self.state_machine = {
                # --------------------------------------------------------
                ('XY', 'L') : { 'EXIT'     : [0,1]                      },
                ('Xy', 'L') : { 'Y_DIRECT' : [0,1], 'Y_DEROUTE' : [0,1] },
                ('xY', 'L') : { 'X_DIRECT' : [0,1], 'X_DEROUTE' : [0,1] },
                ('xy', 'L') : { 'Y_DIRECT' : [0,1], 'Y_DEROUTE' : [0,1] },
                # --------------------------------------------------------
                ('XY', 'X') : { 'EXIT'     : [0,1]                      },
                ('Xy', 'X') : {                                         },
                ('xY', 'X') : { 'X_FINISH' : [1]                        },
                ('xy', 'X') : {                                         },
                # --------------------------------------------------------
                ('XY', 'Y') : { 'EXIT'     : [0,1]                      },
                ('Xy', 'Y') : { 'Y_FINISH' : [1]                        },
                ('xY', 'Y') : { 'X_DIRECT' : [0,1], 'X_DEROUTE' : [0,1] },
                ('xy', 'Y') : { 'Y_FINISH' : [1]                        },
                # --------------------------------------------------------
            }

        #
        # Setup the VCATs, etc
        #
        super().__init__('DOAL', parameters, vc_map)


    def get_threshold(self, port_type, route_type, rc):
        return 2 if rc == 0 else 1


    def get_mask(self, location, port_type, route_type, rc, rc_mask):
        if location == 'XY':                        # we are at the destination switch, use configured egress RCs
            mask = rc_mask[self.egress_rc_type]
        elif 'DEROUTE' in route_type:               # use RC1 for a first hop of two
            mask = rc_mask[1]
        else:                                       # use RC0 for completing a dimension
            mask = rc_mask[0]

        return mask

# ----------------------------------------------------------------------------------------------------------------------

    """
    Another view of the state machine.  This view rearranges the rows to group them by location first.

        if self.dim1 == 'X':

                # --------------------------------------------------------
                ('XY', 'L') : { 'EXIT'     : [0,1]                      },
                ('XY', 'X') : { 'EXIT'     : [0,1]                      },
                ('XY', 'Y') : { 'EXIT'     : [0,1]                      },
                # --------------------------------------------------------
                ('Xy', 'L') : { 'Y_DIRECT' : [0,1], 'Y_DEROUTE' : [0,1] },
                ('Xy', 'X') : { 'Y_DIRECT' : [0,1], 'Y_DEROUTE' : [0,1] },
                ('Xy', 'Y') : { 'Y_FINISH' : [1]                        },
                # --------------------------------------------------------
                ('xY', 'L') : { 'X_DIRECT' : [0,1], 'X_DEROUTE' : [0,1] },
                ('xY', 'X') : { 'X_FINISH' : [1]                        },
                ('xY', 'Y') : {                                         },
                # --------------------------------------------------------
                ('xy', 'L') : { 'X_DIRECT' : [0,1], 'X_DEROUTE' : [0,1] },
                ('xy', 'X') : { 'X_FINISH' : [1]                        },
                ('xy', 'Y') : {                                         },
                # --------------------------------------------------------



        if self.dim1 == 'Y':

                # --------------------------------------------------------
                ('XY', 'L') : { 'EXIT'     : [0,1]                      },
                ('XY', 'X') : { 'EXIT'     : [0,1]                      },
                ('XY', 'Y') : { 'EXIT'     : [0,1]                      },
                # --------------------------------------------------------
                ('Xy', 'L') : { 'Y_DIRECT' : [0,1], 'Y_DEROUTE' : [0,1] },
                ('Xy', 'X') : {                                         },
                ('Xy', 'Y') : { 'Y_FINISH' : [1]                        },
                # --------------------------------------------------------
                ('xY', 'L') : { 'X_DIRECT' : [0,1], 'X_DEROUTE' : [0,1] },
                ('xY', 'X') : { 'X_FINISH' : [1]                        },
                ('xY', 'Y') : { 'X_DIRECT' : [0,1], 'X_DEROUTE' : [0,1] },
                # --------------------------------------------------------
                ('xy', 'L') : { 'Y_DIRECT' : [0,1], 'Y_DEROUTE' : [0,1] },
                ('xy', 'X') : {                                         },
                ('xy', 'Y') : { 'Y_FINISH' : [1]                        },
                # --------------------------------------------------------

    """
