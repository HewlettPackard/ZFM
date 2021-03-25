#!/usr/bin/env python3
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP.
# Licensed under the Apache v2.0 license.
#

from km.routers.NxM import NxM


class DOR(NxM):
    def __init__(self, fabric, parameters, vc_map):
        order_flag = parameters.get('XDimensionFirst', True)
        self.dim1,self.dim2  = ('X','Y') if order_flag else ('Y','X')

        #
        # Routing state machine.  See NxM.route_switch_to_switch() for documentation on format.
        #
        if self.dim1 == 'X':
            self.state_machine = {
                # ---------------------------------
                ('XY', 'L') : { 'EXIT'     : [0] },
                ('Xy', 'L') : { 'Y_DIRECT' : [0] },
                ('xY', 'L') : { 'X_DIRECT' : [0] },
                ('xy', 'L') : { 'X_DIRECT' : [0] },
                # ---------------------------------
                ('XY', 'X') : { 'EXIT'     : [0] },
                ('Xy', 'X') : { 'Y_DIRECT' : [0] },
                ('xY', 'X') : {                  },
                ('xy', 'X') : {                  },
                # ---------------------------------
                ('XY', 'Y') : { 'EXIT'     : [0] },
                ('Xy', 'Y') : {                  },
                ('xY', 'Y') : {                  },
                ('xy', 'Y') : {                  },
                # ---------------------------------
            }
        else:
            self.state_machine = {
                # ---------------------------------
                ('XY', 'L') : { 'EXIT'     : [0] },
                ('Xy', 'L') : { 'Y_DIRECT' : [0] },
                ('xY', 'L') : { 'X_DIRECT' : [0] },
                ('xy', 'L') : { 'Y_DIRECT' : [0] },
                # ---------------------------------
                ('XY', 'X') : { 'EXIT'     : [0] },
                ('Xy', 'X') : {                  },
                ('xY', 'X') : {                  },
                ('xy', 'X') : {                  },
                # ---------------------------------
                ('XY', 'Y') : { 'EXIT'     : [0] },
                ('Xy', 'Y') : {                  },
                ('xY', 'Y') : { 'X_DIRECT' : [0] },
                ('xy', 'Y') : {                  },
                # ---------------------------------
            }

        #
        # Setup the VCATs, etc
        #
        super().__init__('DOR', parameters, vc_map)


    def get_threshold(self, port_type, route_type, rc):
        return 7


    def get_mask(self, location, port_type, route_type, rc, rc_mask):
        return rc_mask[0]           # only RC0 in DOR

# ----------------------------------------------------------------------------------------------------------------------

    """
    Another view of the state machine.  This view rearranges the rows to group them by location first.

        if self.dim1 == 'X':

                # ---------------------------------
                ('XY', 'L') : { 'EXIT'     : [0] },
                ('XY', 'X') : { 'EXIT'     : [0] },
                ('XY', 'Y') : { 'EXIT'     : [0] },
                # ---------------------------------
                ('Xy', 'L') : { 'Y_DIRECT' : [0] },
                ('Xy', 'X') : { 'Y_DIRECT' : [0] },
                ('Xy', 'Y') : {                  },
                # ---------------------------------
                ('xY', 'L') : { 'X_DIRECT' : [0] },
                ('xY', 'X') : {                  },
                ('xY', 'Y') : {                  },
                # ---------------------------------
                ('xy', 'L') : { 'X_DIRECT' : [0] },
                ('xy', 'X') : {                  },
                ('xy', 'Y') : {                  },
                # ---------------------------------



        if self.dim1 == 'Y':

                # ---------------------------------
                ('XY', 'L') : { 'EXIT'     : [0] },
                ('XY', 'X') : { 'EXIT'     : [0] },
                ('XY', 'Y') : { 'EXIT'     : [0] },
                # ---------------------------------
                ('Xy', 'L') : { 'Y_DIRECT' : [0] },
                ('Xy', 'X') : {                  },
                ('Xy', 'Y') : {                  },
                # ---------------------------------
                ('xY', 'L') : { 'X_DIRECT' : [0] },
                ('xY', 'X') : {                  },
                ('xY', 'Y') : { 'X_DIRECT' : [0] },
                # ---------------------------------
                ('xy', 'L') : { 'Y_DIRECT' : [0] },
                ('xy', 'X') : {                  },
                ('xy', 'Y') : {                  },
                # ---------------------------------

    """
