# coding=utf-8
import random
import re
import socket
import struct
from socket import AF_UNSPEC, SOCK_STREAM
from socketserver import BaseRequestHandler, ThreadingTCPServer
from threading import Event, Lock, Thread

# Python package: Client and Server for ModBus/TCP
#        Version: 0.2.0
#        Website: https://github.com/sourceperl/pyModbusTCP
#           Date: 2022-06-05
#        License: MIT (http://http://opensource.org/licenses/mit-license.php)
#    Description: Client/Server ModBus/TCP
#                 Support functions 3 and 16 (class 0)
#                 1,2,4,5,6 (Class 1)
#                 15
#        Charset: utf-8

""" pyModbusTCP package constants definition """

# Package version
VERSION = "0.2.0"
# Modbus/TCP
MODBUS_PORT = 502
# Modbus function code
READ_COILS = 0x01
READ_DISCRETE_INPUTS = 0x02
READ_HOLDING_REGISTERS = 0x03
READ_INPUT_REGISTERS = 0x04
WRITE_SINGLE_COIL = 0x05
WRITE_SINGLE_REGISTER = 0x06
WRITE_MULTIPLE_COILS = 0x0F
WRITE_MULTIPLE_REGISTERS = 0x10
MODBUS_ENCAPSULATED_INTERFACE = 0x2B
SUPPORTED_FUNCTION_CODES = (
    READ_COILS,
    READ_DISCRETE_INPUTS,
    READ_HOLDING_REGISTERS,
    READ_INPUT_REGISTERS,
    WRITE_SINGLE_COIL,
    WRITE_SINGLE_REGISTER,
    WRITE_MULTIPLE_COILS,
    WRITE_MULTIPLE_REGISTERS,
)
# Modbus except code
EXP_NONE = 0x00
EXP_ILLEGAL_FUNCTION = 0x01
EXP_DATA_ADDRESS = 0x02
EXP_DATA_VALUE = 0x03
EXP_SLAVE_DEVICE_FAILURE = 0x04
EXP_ACKNOWLEDGE = 0x05
EXP_SLAVE_DEVICE_BUSY = 0x06
EXP_NEGATIVE_ACKNOWLEDGE = 0x07
EXP_MEMORY_PARITY_ERROR = 0x08
EXP_GATEWAY_PATH_UNAVAILABLE = 0x0A
EXP_GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND = 0x0B
# Exception as short human-readable
EXP_TXT = {
    EXP_NONE: "no exception",
    EXP_ILLEGAL_FUNCTION: "illegal function",
    EXP_DATA_ADDRESS: "illegal data address",
    EXP_DATA_VALUE: "illegal data value",
    EXP_SLAVE_DEVICE_FAILURE: "slave device failure",
    EXP_ACKNOWLEDGE: "acknowledge",
    EXP_SLAVE_DEVICE_BUSY: "slave device busy",
    EXP_NEGATIVE_ACKNOWLEDGE: "negative acknowledge",
    EXP_MEMORY_PARITY_ERROR: "memory parity error",
    EXP_GATEWAY_PATH_UNAVAILABLE: "gateway path unavailable",
    EXP_GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND: "gateway target device failed to respond",
}
# Exception as details human-readable
EXP_DETAILS = {
    EXP_NONE: "The last request produced no exceptions.",
    EXP_ILLEGAL_FUNCTION: "Function code received in the query is not recognized or allowed by slave.",
    EXP_DATA_ADDRESS: "Data address of some or all the required entities are not allowed or do not exist in slave.",
    EXP_DATA_VALUE: "Value is not accepted by slave.",
    EXP_SLAVE_DEVICE_FAILURE: "Unrecoverable error occurred while slave was attempting to perform requested action.",
    EXP_ACKNOWLEDGE: "Slave has accepted request and is processing it, but a long duration of time is required. "
    "This response is returned to prevent a timeout error from occurring in the master. "
    "Master can next issue a Poll Program Complete message to determine whether processing "
    "is completed.",
    EXP_SLAVE_DEVICE_BUSY: "Slave is engaged in processing a long-duration command. Master should retry later.",
    EXP_NEGATIVE_ACKNOWLEDGE: "Slave cannot perform the programming functions. "
    "Master should request diagnostic or error information from slave.",
    EXP_MEMORY_PARITY_ERROR: "Slave detected a parity error in memory. "
    "Master can retry the request, but service may be required on the slave device.",
    EXP_GATEWAY_PATH_UNAVAILABLE: "Specialized for Modbus gateways, this indicates a misconfiguration on gateway.",
    EXP_GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND: "Specialized for Modbus gateways, sent when slave fails to respond.",
}
# Module error codes
MB_NO_ERR = 0
MB_RESOLVE_ERR = 1
MB_CONNECT_ERR = 2
MB_SEND_ERR = 3
MB_RECV_ERR = 4
MB_TIMEOUT_ERR = 5
MB_FRAME_ERR = 6
MB_EXCEPT_ERR = 7
MB_CRC_ERR = 8
MB_SOCK_CLOSE_ERR = 9
# Module error as short human-readable
MB_ERR_TXT = {
    MB_NO_ERR: "no error",
    MB_RESOLVE_ERR: "name resolve error",
    MB_CONNECT_ERR: "connect error",
    MB_SEND_ERR: "socket send error",
    MB_RECV_ERR: "socket recv error",
    MB_TIMEOUT_ERR: "recv timeout occur",
    MB_FRAME_ERR: "frame format error",
    MB_EXCEPT_ERR: "modbus exception",
    MB_CRC_ERR: "bad CRC on receive frame",
    MB_SOCK_CLOSE_ERR: "socket is closed",
}
""" pyModbusTCP package constants definition """

""" pyModbusTCP utils functions """


###############
# bits function
###############
def get_bits_from_int(val_int, val_size=16):
    """Get the list of bits of val_int integer (default size is 16 bits).

    Return bits list, the least significant bit first. Use list.reverse() for msb first.

    :param val_int: integer value
    :type val_int: int
    :param val_size: bit length of integer (word = 16, long = 32) (optional)
    :type val_size: int
    :returns: list of boolean "bits" (the least significant first)
    :rtype: list
    """
    bits = []
    # populate bits list with bool items of val_int
    for i in range(val_size):
        bits.append(bool((val_int >> i) & 0x01))
    # return bits list
    return bits


# short alias
int2bits = get_bits_from_int


def byte_length(bit_length):
    """Return the number of bytes needs to contain a bit_length structure.

    :param bit_length: the number of bits
    :type bit_length: int
    :returns: the number of bytes
    :rtype: int
    """
    return (bit_length + 7) // 8


def test_bit(value, offset):
    """Test a bit at offset position.

    :param value: value of integer to test
    :type value: int
    :param offset: bit offset (0 is lsb)
    :type offset: int
    :returns: value of bit at offset position
    :rtype: bool
    """
    mask = 1 << offset
    return bool(value & mask)


def set_bit(value, offset):
    """Set a bit at offset position.

    :param value: value of integer where set the bit
    :type value: int
    :param offset: bit offset (0 is lsb)
    :type offset: int
    :returns: value of integer with bit set
    :rtype: int
    """
    mask = 1 << offset
    return int(value | mask)


def reset_bit(value, offset):
    """Reset a bit at offset position.

    :param value: value of integer where reset the bit
    :type value: int
    :param offset: bit offset (0 is lsb)
    :type offset: int
    :returns: value of integer with bit reset
    :rtype: int
    """
    mask = ~(1 << offset)
    return int(value & mask)


def toggle_bit(value, offset):
    """Return an integer with the bit at offset position inverted.

    :param value: value of integer where invert the bit
    :type value: int
    :param offset: bit offset (0 is lsb)
    :type offset: int
    :returns: value of integer with bit inverted
    :rtype: int
    """
    mask = 1 << offset
    return int(value ^ mask)


########################
# Word convert functions
########################
def word_list_to_long(val_list, big_endian=True, long_long=False):
    """Word list (16 bits) to long (32 bits) or long long (64 bits) list.

    By default, word_list_to_long() use big endian order. For use little endian, set
    big_endian param to False. Output format could be long long with long_long.
    option set to True.

    :param val_list: list of 16 bits int value
    :type val_list: list
    :param big_endian: True for big endian/False for little (optional)
    :type big_endian: bool
    :param long_long: True for long long 64 bits, default is long 32 bits (optional)
    :type long_long: bool
    :returns: list of 32 bits int value
    :rtype: list
    """
    long_list = []
    block_size = 4 if long_long else 2
    # populate long_list (len is half or quarter of 16 bits val_list) with 32 or 64 bits value
    for index in range(int(len(val_list) / block_size)):
        start = block_size * index
        long = 0
        if big_endian:
            if long_long:
                long += (val_list[start] << 48) + (val_list[start + 1] << 32)
                long += (val_list[start + 2] << 16) + (val_list[start + 3])
            else:
                long += (val_list[start] << 16) + val_list[start + 1]
        else:
            if long_long:
                long += (val_list[start + 3] << 48) + (val_list[start + 2] << 32)
            long += (val_list[start + 1] << 16) + val_list[start]
        long_list.append(long)
    # return long list
    return long_list


# short alias
words2longs = word_list_to_long


def long_list_to_word(val_list, big_endian=True, long_long=False):
    """Long (32 bits) or long long (64 bits) list to word (16 bits) list.

    By default long_list_to_word() use big endian order. For use little endian, set
    big_endian param to False. Input format could be long long with long_long
    param to True.

    :param val_list: list of 32 bits int value
    :type val_list: list
    :param big_endian: True for big endian/False for little (optional)
    :type big_endian: bool
    :param long_long: True for long long 64 bits, default is long 32 bits (optional)
    :type long_long: bool
    :returns: list of 16 bits int value
    :rtype: list
    """
    word_list = []
    # populate 16 bits word_list with 32 or 64 bits value of val_list
    for val in val_list:
        block_l = [val & 0xFFFF, (val >> 16) & 0xFFFF]
        if long_long:
            block_l.append((val >> 32) & 0xFFFF)
            block_l.append((val >> 48) & 0xFFFF)
        if big_endian:
            block_l.reverse()
        word_list.extend(block_l)
    # return long list
    return word_list


# short alias
longs2words = long_list_to_word


##########################
# 2's complement functions
##########################
def get_2comp(val_int, val_size=16):
    """Get the 2's complement of Python int val_int.

    :param val_int: int value to apply 2's complement
    :type val_int: int
    :param val_size: bit size of int value (word = 16, long = 32) (optional)
    :type val_size: int
    :returns: 2's complement result
    :rtype: int
    :raises ValueError: if mismatch between val_int and val_size
    """
    # avoid overflow
    if not (-1 << val_size - 1) <= val_int < (1 << val_size):
        err_msg = "could not compute two's complement for %i on %i bits"
        err_msg %= (val_int, val_size)
        raise ValueError(err_msg)
    # test negative int
    if val_int < 0:
        val_int += 1 << val_size
    # test MSB (do two's comp if set)
    elif val_int & (1 << (val_size - 1)):
        val_int -= 1 << val_size
    return val_int


# short alias
twos_c = get_2comp


def get_list_2comp(val_list, val_size=16):
    """Get the 2's complement of Python list val_list.

    :param val_list: list of int value to apply 2's complement
    :type val_list: list
    :param val_size: bit size of int value (word = 16, long = 32) (optional)
    :type val_size: int
    :returns: 2's complement result
    :rtype: list
    """
    return [get_2comp(val, val_size) for val in val_list]


# short alias
twos_c_l = get_list_2comp


###############################
# IEEE floating-point functions
###############################
def decode_ieee(val_int, double=False):
    """Decode Python int (32 bits integer) as an IEEE single or double precision format.

    Support NaN.

    :param val_int: a 32 or 64 bits integer as an int Python value
    :type val_int: int
    :param double: set to decode as a 64 bits double precision,
                   default is 32 bits single (optional)
    :type double: bool
    :returns: float result
    :rtype: float
    """
    if double:
        return struct.unpack("d", struct.pack("Q", val_int))[0]
    else:
        return struct.unpack("f", struct.pack("I", val_int))[0]


def encode_ieee(val_float, double=False):
    """Encode Python float to int (32 bits integer) as an IEEE single or double precision format.

    Support NaN.

    :param val_float: float value to convert
    :type val_float: float
    :param double: set to encode as a 64 bits double precision,
                   default is 32 bits single (optional)
    :type double: bool
    :returns: IEEE 32 bits (single precision) as Python int
    :rtype: int
    """
    if double:
        return struct.unpack("Q", struct.pack("d", val_float))[0]
    else:
        return struct.unpack("I", struct.pack("f", val_float))[0]


################
# misc functions
################
def crc16(frame):
    """Compute CRC16.

    :param frame: frame
    :type frame: bytes
    :returns: CRC16
    :rtype: int
    """
    crc = 0xFFFF
    for item in frame:
        next_byte = item
        crc ^= next_byte
        for _ in range(8):
            lsb = crc & 1
            crc >>= 1
            if lsb:
                crc ^= 0xA001
    return crc


def valid_host(host_str):
    """Validate a host string.

    Can be an IPv4/6 address or a valid hostname.

    :param host_str: the host string to test
    :type host_str: str
    :returns: True if host_str is valid
    :rtype: bool
    """
    # IPv4 valid address ?
    try:
        socket.inet_pton(socket.AF_INET, host_str)
        return True
    except socket.error:
        pass
    # IPv6 valid address ?
    try:
        socket.inet_pton(socket.AF_INET6, host_str)
        return True
    except socket.error:
        pass
    # valid hostname ?
    if re.match(r"^[a-z][a-z0-9.\-]+$", host_str):
        return True
    # on invalid host
    return False


""" pyModbusTCP utils functions """

""" pyModbusTCP Server """


class DataBank:
    """Data space class with thread safe access functions"""

    def __init__(
        self,
        coils_size=0x10000,
        coils_default_value=False,
        d_inputs_size=0x10000,
        d_inputs_default_value=False,
        h_regs_size=0x10000,
        h_regs_default_value=0,
        i_regs_size=0x10000,
        i_regs_default_value=0,
        virtual_mode=False,
    ):
        """Constructor

        Modbus server data bank constructor.

        :param coils_size: Number of coils to allocate (default is 65536)
        :type coils_size: int
        :param coils_default_value: Coils default value at startup (default is False)
        :type coils_default_value: bool
        :param d_inputs_size: Number of discrete inputs to allocate (default is 65536)
        :type d_inputs_size: int
        :param d_inputs_default_value: Discrete inputs default value at startup (default is False)
        :type d_inputs_default_value: bool
        :param h_regs_size: Number of holding registers to allocate (default is 65536)
        :type h_regs_size: int
        :param h_regs_default_value: Holding registers default value at startup (default is 0)
        :type h_regs_default_value: int
        :param i_regs_size: Number of input registers to allocate (default is 65536)
        :type i_regs_size: int
        :param i_regs_default_value: Input registers default value at startup (default is 0)
        :type i_regs_default_value: int
        :param virtual_mode: Disallow all modbus data space to work with virtual values (default is False)
        :type virtual_mode: bool
        """
        # public
        self.coils_size = int(coils_size)
        self.coils_default_value = bool(coils_default_value)
        self.d_inputs_size = int(d_inputs_size)
        self.d_inputs_default_value = bool(d_inputs_default_value)
        self.h_regs_size = int(h_regs_size)
        self.h_regs_default_value = int(h_regs_default_value)
        self.i_regs_size = int(i_regs_size)
        self.i_regs_default_value = int(i_regs_default_value)
        self.virtual_mode = virtual_mode
        # specific modes (override some values)
        if self.virtual_mode:
            self.coils_size = 0
            self.d_inputs_size = 0
            self.h_regs_size = 0
            self.i_regs_size = 0
        # private
        self._coils_lock = Lock()
        self._coils = [self.coils_default_value] * self.coils_size
        self._d_inputs_lock = Lock()
        self._d_inputs = [self.d_inputs_default_value] * self.d_inputs_size
        self._h_regs_lock = Lock()
        self._h_regs = [self.h_regs_default_value] * self.h_regs_size
        self._i_regs_lock = Lock()
        self._i_regs = [self.i_regs_default_value] * self.i_regs_size

    def __repr__(self):
        attrs_str = ""
        for attr_name in self.__dict__:
            if isinstance(attr_name, str) and not attr_name.startswith("_"):
                if attrs_str:
                    attrs_str += ", "
                attrs_str += "%s=%r" % (attr_name, self.__dict__[attr_name])
        return "DataBank(%s)" % attrs_str

    def get_coils(self, address, number=1, srv_info=None):
        """Read data on server coils space

        :param address: start address
        :type address: int
        :param number: number of bits (optional)
        :type number: int
        :param srv_info: some server info (must be set by server only)
        :type srv_info: ModbusServer.ServerInfo
        :returns: list of bool or None if error
        :rtype: list or None
        """
        # secure extract of data from list used by server thread
        with self._coils_lock:
            if (address >= 0) and (address + number <= len(self._coils)):
                return self._coils[address : number + address]
            else:
                return None

    def set_coils(self, address, bit_list, srv_info=None):
        """Write data to server coils space

        :param address: start address
        :type address: int
        :param bit_list: a list of bool to write
        :type bit_list: list
        :param srv_info: some server info (must be set by server only)
        :type srv_info: ModbusServerInfo
        :returns: True if success or None if error
        :rtype: bool or None
        :raises ValueError: if bit_list members cannot be converted to bool
        """
        # ensure bit_list values are bool
        bit_list = [bool(b) for b in bit_list]
        # keep trace of any changes
        changes_list = []
        # ensure atomic update of internal data
        with self._coils_lock:
            if (address >= 0) and (address + len(bit_list) <= len(self._coils)):
                for offset, c_value in enumerate(bit_list):
                    c_address = address + offset
                    if self._coils[c_address] != c_value:
                        changes_list.append(
                            (c_address, self._coils[c_address], c_value)
                        )
                        self._coils[c_address] = c_value
            else:
                return None
        # on server update
        if srv_info:
            # notify changes with on change method (after atomic update)
            for address, from_value, to_value in changes_list:
                self.on_coils_change(address, from_value, to_value, srv_info)
        return True

    def get_discrete_inputs(self, address, number=1, srv_info=None):
        """Read data on server discrete inputs space

        :param address: start address
        :type address: int
        :param number: number of bits (optional)
        :type number: int
        :param srv_info: some server info (must be set by server only)
        :type srv_info: ModbusServerInfo
        :returns: list of bool or None if error
        :rtype: list or None
        """
        # secure extract of data from list used by server thread
        with self._d_inputs_lock:
            if (address >= 0) and (address + number <= len(self._coils)):
                return self._d_inputs[address : number + address]
            else:
                return None

    def set_discrete_inputs(self, address, bit_list):
        """Write data to server discrete inputs space

        :param address: start address
        :type address: int
        :param bit_list: a list of bool to write
        :type bit_list: list
        :returns: True if success or None if error
        :rtype: bool or None
        :raises ValueError: if bit_list members cannot be converted to bool
        """
        # ensure bit_list values are bool
        bit_list = [bool(b) for b in bit_list]
        # ensure atomic update of internal data
        with self._d_inputs_lock:
            if (address >= 0) and (address + len(bit_list) <= len(self._coils)):
                for offset, b_value in enumerate(bit_list):
                    self._d_inputs[address + offset] = b_value
            else:
                return None
        return True

    def get_holding_registers(self, address, number=1, srv_info=None):
        """Read data on server holding registers space

        :param address: start address
        :type address: int
        :param number: number of words (optional)
        :type number: int
        :param srv_info: some server info (must be set by server only)
        :type srv_info: ModbusServerInfo
        :returns: list of int or None if error
        :rtype: list or None
        """
        # secure extract of data from list used by server thread
        with self._h_regs_lock:
            if (address >= 0) and (address + number <= len(self._h_regs)):
                return self._h_regs[address : number + address]
            else:
                return None

    def set_holding_registers(self, address, word_list, srv_info=None):
        """Write data to server holding registers space

        :param address: start address
        :type address: int
        :param word_list: a list of word to write
        :type word_list: list
        :param srv_info: some server info (must be set by server only)
        :type srv_info: ModbusServerInfo
        :returns: True if success or None if error
        :rtype: bool or None
        :raises ValueError: if word_list members cannot be converted to int
        """
        # ensure word_list values are int with a max bit length of 16
        word_list = [int(w) & 0xFFFF for w in word_list]
        # keep trace of any changes
        changes_list = []
        # ensure atomic update of internal data
        with self._h_regs_lock:
            if (address >= 0) and (address + len(word_list) <= len(self._h_regs)):
                for offset, c_value in enumerate(word_list):
                    c_address = address + offset
                    if self._h_regs[c_address] != c_value:
                        changes_list.append(
                            (c_address, self._h_regs[c_address], c_value)
                        )
                        self._h_regs[c_address] = c_value
            else:
                return None
        # on server update
        if srv_info:
            # notify changes with on change method (after atomic update)
            for address, from_value, to_value in changes_list:
                self.on_holding_registers_change(
                    address, from_value, to_value, srv_info=srv_info
                )
        return True

    def get_input_registers(self, address, number=1, srv_info=None):
        """Read data on server input registers space

        :param address: start address
        :type address: int
        :param number: number of words (optional)
        :type number: int
        :param srv_info: some server info (must be set by server only)
        :type srv_info: ModbusServerInfo
        :returns: list of int or None if error
        :rtype: list or None
        """
        # secure extract of data from list used by server thread
        with self._i_regs_lock:
            if (address >= 0) and (address + number <= len(self._h_regs)):
                return self._i_regs[address : number + address]
            else:
                return None

    def set_input_registers(self, address, word_list):
        """Write data to server input registers space

        :param address: start address
        :type address: int
        :param word_list: a list of word to write
        :type word_list: list
        :returns: True if success or None if error
        :rtype: bool or None
        :raises ValueError: if word_list members cannot be converted to int
        """
        # ensure word_list values are int with a max bit length of 16
        word_list = [int(w) & 0xFFFF for w in word_list]
        # ensure atomic update of internal data
        with self._i_regs_lock:
            if (address >= 0) and (address + len(word_list) <= len(self._h_regs)):
                for offset, c_value in enumerate(word_list):
                    c_address = address + offset
                    if self._i_regs[c_address] != c_value:
                        self._i_regs[c_address] = c_value
            else:
                return None
        return True

    def on_coils_change(self, address, from_value, to_value, srv_info):
        """Call by server when a value change occur in coils space

        This method is provided to be overridden with user code to catch changes

        :param address: address of coil
        :type address: int
        :param from_value: coil original value
        :type from_value: bool
        :param to_value: coil next value
        :type to_value: bool
        :param srv_info: some server info
        :type srv_info: ModbusServerInfo
        """
        pass

    def on_holding_registers_change(self, address, from_value, to_value, srv_info):
        """Call by server when a value change occur in holding registers space

        This method is provided to be overridden with user code to catch changes

        :param address: address of register
        :type address: int
        :param from_value: register original value
        :type from_value: int
        :param to_value: register next value
        :type to_value: int
        :param srv_info: some server info
        :type srv_info: ModbusServerInfo
        """
        pass


class DataHandler:
    """Default data handler for ModbusServer, map server threads calls to DataBank.

    Custom handler must derive from this class.
    """

    class Return:
        def __init__(self, exp_code, data=None):
            self.exp_code = exp_code
            self.data = data

        @property
        def ok(self):
            return self.exp_code == EXP_NONE

    def __init__(self, data_bank=None):
        """Constructor

        Modbus server data handler constructor.

        :param data_bank: a reference to custom DefaultDataBank
        :type data_bank: DataBank
        """
        # check data_bank type
        if data_bank and not isinstance(data_bank, DataBank):
            raise ValueError("data_bank arg is invalid")
        # public
        self.data_bank = data_bank or DataBank()

    def __repr__(self):
        return "ModbusServerDataHandler(data_bank=%s)" % self.data_bank

    def read_coils(self, address, count, srv_info):
        """Call by server for reading in coils space

        :param address: start address
        :type address: int
        :param count: number of coils
        :type count: int
        :param srv_info: some server info
        :type srv_info: ModbusServer.ServerInfo
        :rtype: Return
        """
        # read bits from DataBank
        bits_l = self.data_bank.get_coils(address, count, srv_info)
        # return DataStatus to server
        if bits_l is not None:
            return DataHandler.Return(exp_code=EXP_NONE, data=bits_l)
        else:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)

    def write_coils(self, address, bits_l, srv_info):
        """Call by server for writing in the coils space

        :param address: start address
        :type address: int
        :param bits_l: list of boolean to write
        :type bits_l: list
        :param srv_info: some server info
        :type srv_info: ModbusServer.ServerInfo
        :rtype: Return
        """
        # write bits to DataBank
        update_ok = self.data_bank.set_coils(address, bits_l, srv_info)
        # return DataStatus to server
        if update_ok:
            return DataHandler.Return(exp_code=EXP_NONE)
        else:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)

    def read_d_inputs(self, address, count, srv_info):
        """Call by server for reading in the discrete inputs space

        :param address: start address
        :type address: int
        :param count: number of discrete inputs
        :type count: int
        :param srv_info: some server info
        :type srv_info: ModbusServer.ServerInfo
        :rtype: Return
        """
        # read bits from DataBank
        bits_l = self.data_bank.get_discrete_inputs(address, count, srv_info)
        # return DataStatus to server
        if bits_l is not None:
            return DataHandler.Return(exp_code=EXP_NONE, data=bits_l)
        else:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)

    def read_h_regs(self, address, count, srv_info):
        """Call by server for reading in the holding registers space

        :param address: start address
        :type address: int
        :param count: number of holding registers
        :type count: int
        :param srv_info: some server info
        :type srv_info: ModbusServer.ServerInfo
        :rtype: Return
        """
        # read words from DataBank
        words_l = self.data_bank.get_holding_registers(address, count, srv_info)
        # return DataStatus to server
        if words_l is not None:
            return DataHandler.Return(exp_code=EXP_NONE, data=words_l)
        else:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)

    def write_h_regs(self, address, words_l, srv_info):
        """Call by server for writing in the holding registers space

        :param address: start address
        :type address: int
        :param words_l: list of word value to write
        :type words_l: list
        :param srv_info: some server info
        :type srv_info: ModbusServer.ServerInfo
        :rtype: Return
        """
        # write words to DataBank
        update_ok = self.data_bank.set_holding_registers(address, words_l, srv_info)
        # return DataStatus to server
        if update_ok:
            return DataHandler.Return(exp_code=EXP_NONE)
        else:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)

    def read_i_regs(self, address, count, srv_info):
        """Call by server for reading in the input registers space

        :param address: start address
        :type address: int
        :param count: number of input registers
        :type count: int
        :param srv_info: some server info
        :type srv_info: ModbusServer.ServerInfo
        :rtype: Return
        """
        # read words from DataBank
        words_l = self.data_bank.get_input_registers(address, count, srv_info)
        # return DataStatus to server
        if words_l is not None:
            return DataHandler.Return(exp_code=EXP_NONE, data=words_l)
        else:
            return DataHandler.Return(exp_code=EXP_DATA_ADDRESS)


class ModbusServer:
    """Modbus TCP server"""

    class Error(Exception):
        """Base exception for ModbusServer related errors."""

        pass

    class NetworkError(Error):
        """Exception raise by ModbusServer on I/O errors."""

        pass

    class DataFormatError(Error):
        """Exception raise by ModbusServer for data format errors."""

        pass

    class ClientInfo:
        """Container class for client information"""

        def __init__(self, address="", port=0):
            self.address = address
            self.port = port

        def __repr__(self):
            return "ClientInfo(address=%r, port=%r)" % (self.address, self.port)

    class ServerInfo:
        """Container class for server information"""

        def __init__(self):
            self.client = ModbusServer.ClientInfo()
            self.recv_frame = ModbusServer.Frame()

    class SessionData:
        """Container class for server session data."""

        def __init__(self):
            self.client = ModbusServer.ClientInfo()
            self.request = ModbusServer.Frame()
            self.response = ModbusServer.Frame()

        @property
        def srv_info(self):
            info = ModbusServer.ServerInfo()
            info.client = self.client
            info.recv_frame = self.request
            return info

        def new_request(self):
            self.request = ModbusServer.Frame()
            self.response = ModbusServer.Frame()

        def set_response_mbap(self):
            self.response.mbap.transaction_id = self.request.mbap.transaction_id
            self.response.mbap.protocol_id = self.request.mbap.protocol_id
            self.response.mbap.unit_id = self.request.mbap.unit_id

    class Frame:
        def __init__(self):
            """Modbus Frame container."""
            self.mbap = ModbusServer.MBAP()
            self.pdu = ModbusServer.PDU()

        @property
        def raw(self):
            self.mbap.length = len(self.pdu) + 1
            return self.mbap.raw + self.pdu.raw

    class MBAP:
        """MBAP (Modbus Application Protocol) container class."""

        def __init__(self, transaction_id=0, protocol_id=0, length=0, unit_id=0):
            # public
            self.transaction_id = transaction_id
            self.protocol_id = protocol_id
            self.length = length
            self.unit_id = unit_id

        @property
        def raw(self):
            try:
                return struct.pack(
                    ">HHHB",
                    self.transaction_id,
                    self.protocol_id,
                    self.length,
                    self.unit_id,
                )
            except struct.error as e:
                raise ModbusServer.DataFormatError("MBAP raw encode pack error: %s" % e)

        @raw.setter
        def raw(self, value):
            # close connection if no standard 7 bytes mbap header
            if not (value and len(value) == 7):
                raise ModbusServer.DataFormatError("MBAP must have a length of 7 bytes")
            # decode header
            (
                self.transaction_id,
                self.protocol_id,
                self.length,
                self.unit_id,
            ) = struct.unpack(">HHHB", value)
            # check frame header content inconsistency
            if self.protocol_id != 0:
                raise ModbusServer.DataFormatError("MBAP protocol ID must be 0")
            if not 2 < self.length < 256:
                raise ModbusServer.DataFormatError(
                    "MBAP length must be between 2 and 256"
                )

    class PDU:
        """PDU (Protocol Data Unit) container class."""

        def __init__(self, raw=b""):
            """
            Constructor

            :param raw: raw PDU
            :type raw: bytes
            """
            self.raw = raw

        def __len__(self):
            return len(self.raw)

        @property
        def func_code(self):
            return self.raw[0]

        @property
        def except_code(self):
            return self.raw[1]

        @property
        def is_except(self):
            return self.func_code > 0x7F

        @property
        def is_valid(self):
            # PDU min length is 2 bytes
            return self.__len__() < 2

        def clear(self):
            self.raw = b""

        def build_except(self, func_code, exp_status):
            self.clear()
            self.add_pack("BB", func_code + 0x80, exp_status)
            return self

        def add_pack(self, fmt, *args):
            try:
                self.raw += struct.pack(fmt, *args)
            except struct.error:
                err_msg = "unable to format PDU message (fmt: %s, values: %s)" % (
                    fmt,
                    args,
                )
                raise ModbusServer.DataFormatError(err_msg)

        def unpack(self, fmt, from_byte=None, to_byte=None):
            raw_section = self.raw[from_byte:to_byte]
            try:
                return struct.unpack(fmt, raw_section)
            except struct.error:
                err_msg = "unable to decode PDU message  (fmt: %s, values: %s)" % (
                    fmt,
                    raw_section,
                )
                raise ModbusServer.DataFormatError(err_msg)

    class ModbusService(BaseRequestHandler):
        @property
        def server_running(self):
            return self.server.evt_running.is_set()

        def _send_all(self, data):
            try:
                self.request.sendall(data)
                return True
            except socket.timeout:
                return False

        def _recv_all(self, size):
            data = b""
            while len(data) < size:
                try:
                    # avoid keeping this TCP thread run after server.stop() on main server
                    if not self.server_running:
                        raise ModbusServer.NetworkError("main server is not running")
                    # recv all data or a chunk of it
                    data_chunk = self.request.recv(size - len(data))
                    # check data chunk
                    if data_chunk:
                        data += data_chunk
                    else:
                        raise ModbusServer.NetworkError("recv return null")
                except socket.timeout:
                    # just redo main server run test and recv operations on timeout
                    pass
            return data

        def setup(self):
            # set a socket timeout of 1s on blocking operations (like send/recv)
            # this avoids hang thread deletion when main server exit (see _recv_all method)
            self.request.settimeout(1.0)

        def handle(self):
            # try/except end current thread on ModbusServer._InternalError or socket.error
            # this also close the current TCP session associated with it
            # init and update server info structure
            # node.warn(f"{self.client_address = }")
            session_data = ModbusServer.SessionData()
            (
                session_data.client.address,
                session_data.client.port,
            ) = self.client_address
            # debug message
            node.warn("Accept new connection from %r" % session_data.client)
            try:
                # main processing loop
                while True:
                    # node.warn("init session data for new request")
                    # init session data for new request
                    session_data.new_request()

                    # node.warn("receive mbap from client")
                    # receive mbap from client
                    session_data.request.mbap.raw = self._recv_all(7)

                    # node.warn("receive pdu from client")
                    # receive pdu from client
                    session_data.request.pdu.raw = self._recv_all(
                        session_data.request.mbap.length - 1
                    )

                    # node.warn("update response MBAP fields with request data")
                    # update response MBAP fields with request data
                    session_data.set_response_mbap()

                    # node.warn("pass the current session data to request engine")
                    # pass the current session data to request engine
                    self.server.engine(session_data)

                    # node.warn("send the tx pdu with the last rx mbap (only length field change)")
                    # send the tx pdu with the last rx mbap (only length field change)
                    self._send_all(session_data.response.raw)
            except (ModbusServer.Error, socket.error) as e:
                # debug message
                node.warn("Exception during request handling: %r" % e)
                # on main loop except: exit from it and cleanly close the current socket
                self.request.close()

    def __init__(
        self,
        host="localhost",
        port=502,
        no_block=False,
        ipv6=False,
        data_bank=None,
        data_hdl=None,
        ext_engine=None,
    ):
        """Constructor

        Modbus server constructor.

        :param host: hostname or IPv4/IPv6 address server address (default is 'localhost')
        :type host: str
        :param port: TCP port number (default is 502)
        :type port: int
        :param no_block: no block mode, i.e. start() will return (default is False)
        :type no_block: bool
        :param ipv6: use ipv6 stack (default is False)
        :type ipv6: bool
        :param data_bank: instance of custom data bank, if you don't want the default one (optional)
        :type data_bank: DataBank
        :param data_hdl: instance of custom data handler, if you don't want the default one (optional)
        :type data_hdl: DataHandler
        :param ext_engine: an external engine reference (ref to ext_engine(session_data)) (optional)
        :type ext_engine: callable
        """
        # public
        self.host = host
        self.port = port
        self.no_block = no_block
        self.ipv6 = ipv6
        self.ext_engine = ext_engine
        self.data_hdl = None
        self.data_bank = None
        # if external engine is defined, ignore data_hdl and data_bank
        if ext_engine:
            if not callable(self.ext_engine):
                raise ValueError("ext_engine must be callable")
        else:
            # default data handler is ModbusServerDataHandler or a child of it
            if data_hdl is None:
                self.data_hdl = DataHandler(data_bank=data_bank)
            elif isinstance(data_hdl, DataHandler):
                self.data_hdl = data_hdl
                if data_bank:
                    raise ValueError(
                        "when data_hdl is set, you must define data_bank in it"
                    )
            else:
                raise ValueError(
                    "data_hdl is not a ModbusServerDataHandler (or child of it) instance"
                )
            # data bank shortcut
            self.data_bank = self.data_hdl.data_bank
        # private
        self._evt_running = Event()
        self._service = None
        self._serve_th = None
        # modbus default functions map
        self._func_map = {
            READ_COILS: self._read_bits,
            READ_DISCRETE_INPUTS: self._read_bits,
            READ_HOLDING_REGISTERS: self._read_words,
            READ_INPUT_REGISTERS: self._read_words,
            WRITE_SINGLE_COIL: self._write_single_coil,
            WRITE_SINGLE_REGISTER: self._write_single_register,
            WRITE_MULTIPLE_COILS: self._write_multiple_coils,
            WRITE_MULTIPLE_REGISTERS: self._write_multiple_registers,
        }

    def __repr__(self):
        r_str = "ModbusServer(host='%s', port=%d, no_block=%s, ipv6=%s, data_bank=%s, data_hdl=%s, ext_engine=%s)"
        r_str %= (
            self.host,
            self.port,
            self.no_block,
            self.ipv6,
            self.data_bank,
            self.data_hdl,
            self.ext_engine,
        )
        return r_str

    def _engine(self, session_data):
        """Main request processing engine.

        :type session_data: ModbusServer.SessionData
        """
        # call external engine or internal one (if ext_engine undefined)
        if callable(self.ext_engine):
            try:
                self.ext_engine(session_data)
            except Exception as e:
                raise ModbusServer.Error("external engine raise an exception: %r" % e)
        else:
            self._internal_engine(session_data)

    def _internal_engine(self, session_data):
        """Default internal processing engine: call default modbus func.

        :type session_data: ModbusServer.SessionData
        """
        try:
            # call the ad-hoc function, if none exists, send an "illegal function" exception
            func = self._func_map[session_data.request.pdu.func_code]
            # check function found is callable
            if not callable(func):
                raise ValueError
            # call ad-hoc func
            func(session_data)
        except (ValueError, KeyError):
            session_data.response.pdu.build_except(
                session_data.request.pdu.func_code, EXP_ILLEGAL_FUNCTION
            )

    def _read_bits(self, session_data):
        """
        Functions Read Coils (0x01) or Read Discrete Inputs (0x02).

        :param session_data: server engine data
        :type session_data: ModbusServer.SessionData
        """
        # pdu alias
        recv_pdu = session_data.request.pdu
        send_pdu = session_data.response.pdu
        # decode pdu
        (start_address, quantity_bits) = recv_pdu.unpack(">HH", from_byte=1, to_byte=5)
        # check quantity of requested bits
        if 0x0001 <= quantity_bits <= 0x07D0:
            # data handler read request: for coils or discrete inputs space
            if recv_pdu.func_code == READ_COILS:
                ret_hdl = self.data_hdl.read_coils(
                    start_address, quantity_bits, session_data.srv_info
                )
            else:
                ret_hdl = self.data_hdl.read_d_inputs(
                    start_address, quantity_bits, session_data.srv_info
                )
            # format regular or except response
            if ret_hdl.ok:
                # allocate bytes list
                b_size = (quantity_bits + 7) // 8
                bytes_l = [0] * b_size
                # populate bytes list with data bank bits
                for i, item in enumerate(ret_hdl.data):
                    if item:
                        bytes_l[i // 8] = set_bit(bytes_l[i // 8], i % 8)
                # build pdu
                send_pdu.add_pack("BB", recv_pdu.func_code, len(bytes_l))
                send_pdu.add_pack("%dB" % len(bytes_l), *bytes_l)
            else:
                send_pdu.build_except(recv_pdu.func_code, ret_hdl.exp_code)
        else:
            send_pdu.build_except(recv_pdu.func_code, EXP_DATA_VALUE)

    def _read_words(self, session_data):
        """
        Functions Read Holding Registers (0x03) or Read Input Registers (0x04).

        :param session_data: server engine data
        :type session_data: ModbusServer.SessionData
        """
        # pdu alias
        recv_pdu = session_data.request.pdu
        send_pdu = session_data.response.pdu
        # decode pdu
        (start_addr, quantity_regs) = recv_pdu.unpack(">HH", from_byte=1, to_byte=5)
        # check quantity of requested words
        if 0x0001 <= quantity_regs <= 0x007D:
            # data handler read request: for holding or input registers space
            if recv_pdu.func_code == READ_HOLDING_REGISTERS:
                ret_hdl = self.data_hdl.read_h_regs(
                    start_addr, quantity_regs, session_data.srv_info
                )
            else:
                ret_hdl = self.data_hdl.read_i_regs(
                    start_addr, quantity_regs, session_data.srv_info
                )
            # format regular or except response
            if ret_hdl.ok:
                # build pdu
                send_pdu.add_pack("BB", recv_pdu.func_code, quantity_regs * 2)
                # add_pack requested words
                send_pdu.add_pack(">%dH" % len(ret_hdl.data), *ret_hdl.data)
            else:
                send_pdu.build_except(recv_pdu.func_code, ret_hdl.exp_code)
        else:
            send_pdu.build_except(recv_pdu.func_code, EXP_DATA_VALUE)

    def _write_single_coil(self, session_data):
        """
        Function Write Single Coil (0x05).

        :param session_data: server engine data
        :type session_data: ModbusServer.SessionData
        """
        # pdu alias
        recv_pdu = session_data.request.pdu
        send_pdu = session_data.response.pdu
        # decode pdu
        (coil_addr, coil_value) = recv_pdu.unpack(">HH", from_byte=1, to_byte=5)
        # format coil raw value to bool
        coil_as_bool = bool(coil_value == 0xFF00)
        # data handler update request
        ret_hdl = self.data_hdl.write_coils(
            coil_addr, [coil_as_bool], session_data.srv_info
        )
        # format regular or except response
        if ret_hdl.ok:
            send_pdu.add_pack(">BHH", recv_pdu.func_code, coil_addr, coil_value)
        else:
            send_pdu.build_except(recv_pdu.func_code, ret_hdl.exp_code)

    def _write_single_register(self, session_data):
        """
        Functions Write Single Register (0x06).

        :param session_data: server engine data
        :type session_data: ModbusServer.SessionData
        """
        # pdu alias
        recv_pdu = session_data.request.pdu
        send_pdu = session_data.response.pdu
        # decode pdu
        (reg_addr, reg_value) = recv_pdu.unpack(">HH", from_byte=1, to_byte=5)
        # data handler update request
        ret_hdl = self.data_hdl.write_h_regs(
            reg_addr, [reg_value], session_data.srv_info
        )
        # format regular or except response
        if ret_hdl.ok:
            send_pdu.add_pack(">BHH", recv_pdu.func_code, reg_addr, reg_value)
        else:
            send_pdu.build_except(recv_pdu.func_code, ret_hdl.exp_code)

    def _write_multiple_coils(self, session_data):
        """
        Function Write Multiple Coils (0x0F).

        :param session_data: server engine data
        :type session_data: ModbusServer.SessionData
        """
        # pdu alias
        recv_pdu = session_data.request.pdu
        send_pdu = session_data.response.pdu
        # decode pdu
        (start_addr, quantity_bits, byte_count) = recv_pdu.unpack(
            ">HHB", from_byte=1, to_byte=6
        )
        # ok flags: some tests on pdu fields
        qty_bits_ok = 0x0001 <= quantity_bits <= 0x07B0
        b_count_ok = byte_count >= (quantity_bits + 7) // 8
        pdu_len_ok = len(recv_pdu.raw[6:]) >= byte_count
        # test ok flags
        if qty_bits_ok and b_count_ok and pdu_len_ok:
            # allocate bits list
            bits_l = [False] * quantity_bits
            # populate bits list with bits from rx frame
            for i, _ in enumerate(bits_l):
                bit_val = recv_pdu.raw[i // 8 + 6]
                bits_l[i] = test_bit(bit_val, i % 8)
            # data handler update request
            ret_hdl = self.data_hdl.write_coils(
                start_addr, bits_l, session_data.srv_info
            )
            # format regular or except response
            if ret_hdl.ok:
                send_pdu.add_pack(">BHH", recv_pdu.func_code, start_addr, quantity_bits)
            else:
                send_pdu.build_except(recv_pdu.func_code, ret_hdl.exp_code)
        else:
            send_pdu.build_except(recv_pdu.func_code, EXP_DATA_VALUE)

    def _write_multiple_registers(self, session_data):
        """
        Function Write Multiple Registers (0x10).

        :param session_data: server engine data
        :type session_data: ModbusServer.SessionData
        """
        # pdu alias
        recv_pdu = session_data.request.pdu
        send_pdu = session_data.response.pdu
        # decode pdu
        (start_addr, quantity_regs, byte_count) = recv_pdu.unpack(
            ">HHB", from_byte=1, to_byte=6
        )
        # ok flags: some tests on pdu fields
        qty_regs_ok = 0x0001 <= quantity_regs <= 0x007B
        b_count_ok = byte_count == quantity_regs * 2
        pdu_len_ok = len(recv_pdu.raw[6:]) >= byte_count
        # test ok flags
        if qty_regs_ok and b_count_ok and pdu_len_ok:
            # allocate words list
            regs_l = [0] * quantity_regs
            # populate words list with words from rx frame
            for i, _ in enumerate(regs_l):
                offset = i * 2 + 6
                regs_l[i] = recv_pdu.unpack(">H", from_byte=offset, to_byte=offset + 2)[
                    0
                ]
            # data handler update request
            ret_hdl = self.data_hdl.write_h_regs(
                start_addr, regs_l, session_data.srv_info
            )
            # format regular or except response
            if ret_hdl.ok:
                send_pdu.add_pack(">BHH", recv_pdu.func_code, start_addr, quantity_regs)
            else:
                send_pdu.build_except(recv_pdu.func_code, ret_hdl.exp_code)
        else:
            send_pdu.build_except(recv_pdu.func_code, EXP_DATA_VALUE)

    def start(self):
        """Start the server.

        This function will block (or not if no_block flag is set).
        """
        # do nothing if server is already running
        if not self.is_run:
            # set class attribute
            ThreadingTCPServer.address_family = (
                socket.AF_INET6 if self.ipv6 else socket.AF_INET
            )
            ThreadingTCPServer.daemon_threads = True
            # init server
            self._service = ThreadingTCPServer(
                (self.host, self.port), self.ModbusService, bind_and_activate=False
            )
            # pass some things shared with server threads (access via self.server in ModbusService.handle())
            self._service.evt_running = self._evt_running
            self._service.engine = self._engine
            # set socket options
            self._service.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._service.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # TODO test no_delay with bench
            self._service.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # bind and activate
            try:
                self._service.server_bind()
                self._service.server_activate()
            except OSError as e:
                raise ModbusServer.NetworkError(e)
            # serve request
            if self.no_block:
                self._serve_th = Thread(target=self._serve)
                self._serve_th.daemon = True
                self._serve_th.start()
            else:
                self._serve()

    def stop(self):
        """Stop the server."""
        if self.is_run:
            self._service.shutdown()
            self._service.server_close()

    @property
    def is_run(self):
        """Return True if server running."""
        return self._evt_running.is_set()

    def _serve(self):
        try:
            self._evt_running.set()
            self._service.serve_forever()
        except Exception:
            self._service.server_close()
            raise
        except KeyboardInterrupt:
            self._service.server_close()
        finally:
            self._evt_running.clear()


""" pyModbusTCP Server """

""" pyModbusTCP Client """


class ModbusClient(object):
    """Modbus TCP client"""

    class _InternalError(Exception):
        pass

    class _NetworkError(_InternalError):
        def __init__(self, code, message):
            self.code = code
            self.message = message

    class _ModbusExcept(_InternalError):
        def __init__(self, code):
            self.code = code

    def __init__(
        self,
        host="localhost",
        port=502,
        unit_id=1,
        timeout=30.0,
        debug=False,
        auto_open=True,
        auto_close=False,
    ):
        """Constructor.

        :param host: hostname or IPv4/IPv6 address server address
        :type host: str
        :param port: TCP port number
        :type port: int
        :param unit_id: unit ID
        :type unit_id: int
        :param timeout: socket timeout in seconds
        :type timeout: float
        :param debug: debug state
        :type debug: bool
        :param auto_open: auto TCP connect
        :type auto_open: bool
        :param auto_close: auto TCP close)
        :type auto_close: bool
        :return: Object ModbusClient
        :rtype: ModbusClient
        """
        # private
        # internal variables
        self._host = None
        self._port = None
        self._unit_id = None
        self._timeout = None
        self._debug = None
        self._auto_open = None
        self._auto_close = None
        self._sock = None  # socket
        self._transaction_id = 0  # MBAP transaction ID
        self._version = VERSION  # this package version number
        self._last_error = MB_NO_ERR  # last error code
        self._last_except = EXP_NONE  # last except code
        # public
        # constructor arguments: validate them with property setters
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.debug = debug
        self.auto_open = auto_open
        self.auto_close = auto_close

    def __repr__(self):
        r_str = "ModbusClient(host='%s', port=%d, unit_id=%d, timeout=%.2f, debug=%s, auto_open=%s, auto_close=%s)"
        r_str %= (
            self.host,
            self.port,
            self.unit_id,
            self.timeout,
            self.debug,
            self.auto_open,
            self.auto_close,
        )
        return r_str

    def __del__(self):
        self.close()

    @property
    def version(self):
        """Return the current package version as a str."""
        return self._version

    @property
    def last_error(self):
        """Last error code."""
        return self._last_error

    @property
    def last_error_as_txt(self):
        """Human-readable text that describe last error."""
        return MB_ERR_TXT.get(self._last_error, "unknown error")

    @property
    def last_except(self):
        """Return the last modbus exception code."""
        return self._last_except

    @property
    def last_except_as_txt(self):
        """Short human-readable text that describe last modbus exception."""
        default_str = "unreferenced exception 0x%X" % self._last_except
        return EXP_TXT.get(self._last_except, default_str)

    @property
    def last_except_as_full_txt(self):
        """Verbose human-readable text that describe last modbus exception."""
        default_str = "unreferenced exception 0x%X" % self._last_except
        return EXP_DETAILS.get(self._last_except, default_str)

    @property
    def host(self):
        """Get or set the server to connect to.

        This can be any string with a valid IPv4 / IPv6 address or hostname.
        Setting host to a new value will close the current socket.
        """
        return self._host

    @host.setter
    def host(self, value):
        # check type
        if type(value) is not str:
            raise TypeError("host must be a str")
        # check value
        if valid_host(value):
            if self._host != value:
                self.close()
                self._host = value
            return
        # can't be set
        raise ValueError("host can't be set (not a valid IP address or hostname)")

    @property
    def port(self):
        """Get or set the current TCP port (default is 502).

        Setting port to a new value will close the current socket.
        """
        return self._port

    @port.setter
    def port(self, value):
        # check type
        if type(value) is not int:
            raise TypeError("port must be an int")
        # check validity
        if 0 < value < 65536:
            if self._port != value:
                self.close()
                self._port = value
            return
        # can't be set
        raise ValueError("port can't be set (valid if 0 < port < 65536)")

    @property
    def unit_id(self):
        """Get or set the modbus unit identifier (default is 1).

        Any int from 0 to 255 is valid.
        """
        return self._unit_id

    @unit_id.setter
    def unit_id(self, value):
        # check type
        if type(value) is not int:
            raise TypeError("unit_id must be an int")
        # check validity
        if 0 <= value <= 255:
            self._unit_id = value
            return
        # can't be set
        raise ValueError("unit_id can't be set (valid from 0 to 255)")

    @property
    def timeout(self):
        """Get or set requests timeout (default is 30 seconds).

        The argument may be a floating point number for sub-second precision.
        Setting timeout to a new value will close the current socket.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        # enforce type
        value = float(value)
        # check validity
        if 0 < value < 3600:
            if self._timeout != value:
                self.close()
                self._timeout = value
            return
        # can't be set
        raise ValueError("timeout can't be set (valid between 0 and 3600)")

    @property
    def debug(self):
        """Get or set the debug flag (True = turn on)."""
        return self._debug

    @debug.setter
    def debug(self, value):
        # enforce type
        self._debug = bool(value)

    @property
    def auto_open(self):
        """Get or set automatic TCP connect mode (True = turn on)."""
        return self._auto_open

    @auto_open.setter
    def auto_open(self, value):
        # enforce type
        self._auto_open = bool(value)

    @property
    def auto_close(self):
        """Get or set automatic TCP close after each request mode (True = turn on)."""
        return self._auto_close

    @auto_close.setter
    def auto_close(self, value):
        # enforce type
        self._auto_close = bool(value)

    @property
    def is_open(self):
        """Get current status of the TCP connection (True = open)."""
        if self._sock:
            return self._sock.fileno() > 0
        else:
            return False

    def open(self):
        """Connect to modbus server (open TCP connection).

        :returns: connect status (True on success)
        :rtype: bool
        """
        try:
            self._open()
            return True
        except ModbusClient._NetworkError as e:
            self._req_except_handler(e)
            return False

    def _open(self):
        """Connect to modbus server (open TCP connection)."""
        # open an already open socket -> reset it
        if self.is_open:
            self.close()
        # init socket and connect
        # list available sockets on the target host/port
        # AF_xxx : AF_INET -> IPv4, AF_INET6 -> IPv6,
        #          AF_UNSPEC -> IPv6 (priority on some system) or 4
        # list available socket on target host
        for res in socket.getaddrinfo(self.host, self.port, AF_UNSPEC, SOCK_STREAM):
            af, sock_type, proto, canon_name, sa = res
            try:
                self._sock = socket.socket(af, sock_type, proto)
            except socket.error:
                continue
            try:
                self._sock.settimeout(self.timeout)
                self._sock.connect(sa)
            except socket.error:
                self._sock.close()
                continue
            break
        # check connect status
        if not self.is_open:
            raise ModbusClient._NetworkError(MB_CONNECT_ERR, "connection refused")

    def close(self):
        """Close current TCP connection."""
        if self._sock:
            self._sock.close()

    def custom_request(self, pdu):
        """Send a custom modbus request.

        :param pdu: a modbus PDU (protocol data unit)
        :type pdu: bytes
        :returns: modbus frame PDU or None if error
        :rtype: bytes or None
        """
        # make request
        try:
            return self._req_pdu(pdu)
        # handle errors during request
        except ModbusClient._InternalError as e:
            self._req_except_handler(e)
            return None

    def read_coils(self, bit_addr, bit_nb=1):
        """Modbus function READ_COILS (0x01).

        :param bit_addr: bit address (0 to 65535)
        :type bit_addr: int
        :param bit_nb: number of bits to read (1 to 2000)
        :type bit_nb: int
        :returns: bits list or None if error
        :rtype: list of bool or None
        """
        # check params
        if not 0 <= int(bit_addr) <= 0xFFFF:
            raise ValueError("bit_addr out of range (valid from 0 to 65535)")
        if not 1 <= int(bit_nb) <= 2000:
            raise ValueError("bit_nb out of range (valid from 1 to 2000)")
        if int(bit_addr) + int(bit_nb) > 0x10000:
            raise ValueError("read after end of modbus address space")
        # make request
        try:
            tx_pdu = struct.pack(">BHH", READ_COILS, bit_addr, bit_nb)
            rx_pdu = self._req_pdu(tx_pdu=tx_pdu, rx_min_len=3)
            # field "byte count" from PDU
            byte_count = rx_pdu[1]
            # coils PDU part
            rx_pdu_coils = rx_pdu[2:]
            # check rx_byte_count: match nb of bits request and check buffer size
            if byte_count < byte_length(bit_nb) or byte_count != len(rx_pdu_coils):
                raise ModbusClient._NetworkError(MB_RECV_ERR, "rx byte count mismatch")
            # allocate coils list to return
            ret_coils = [False] * bit_nb
            # populate it with coils value from the rx PDU
            for i in range(bit_nb):
                ret_coils[i] = bool((rx_pdu_coils[i // 8] >> i % 8) & 0x01)
            # return read coils
            return ret_coils
        # handle error during request
        except ModbusClient._InternalError as e:
            self._req_except_handler(e)
            return None

    def read_discrete_inputs(self, bit_addr, bit_nb=1):
        """Modbus function READ_DISCRETE_INPUTS (0x02).

        :param bit_addr: bit address (0 to 65535)
        :type bit_addr: int
        :param bit_nb: number of bits to read (1 to 2000)
        :type bit_nb: int
        :returns: bits list or None if error
        :rtype: list of bool or None
        """
        # check params
        if not 0 <= int(bit_addr) <= 0xFFFF:
            raise ValueError("bit_addr out of range (valid from 0 to 65535)")
        if not 1 <= int(bit_nb) <= 2000:
            raise ValueError("bit_nb out of range (valid from 1 to 2000)")
        if int(bit_addr) + int(bit_nb) > 0x10000:
            raise ValueError("read after end of modbus address space")
        # make request
        try:
            tx_pdu = struct.pack(">BHH", READ_DISCRETE_INPUTS, bit_addr, bit_nb)
            rx_pdu = self._req_pdu(tx_pdu=tx_pdu, rx_min_len=3)
            # extract field "byte count"
            byte_count = rx_pdu[1]
            # frame with bits value -> bits[] list
            rx_pdu_d_inputs = rx_pdu[2:]
            # check rx_byte_count: match nb of bits request and check buffer size
            if byte_count < byte_length(bit_nb) or byte_count != len(rx_pdu_d_inputs):
                raise ModbusClient._NetworkError(MB_RECV_ERR, "rx byte count mismatch")
            # allocate a bit_nb size list
            bits = [False] * bit_nb
            # fill bits list with bit items
            for i in range(bit_nb):
                bits[i] = bool((rx_pdu_d_inputs[i // 8] >> i % 8) & 0x01)
            # return bits list
            return bits
        # handle error during request
        except ModbusClient._InternalError as e:
            self._req_except_handler(e)
            return None

    def read_holding_registers(self, reg_addr, reg_nb=1):
        """Modbus function READ_HOLDING_REGISTERS (0x03).

        :param reg_addr: register address (0 to 65535)
        :type reg_addr: int
        :param reg_nb: number of registers to read (1 to 125)
        :type reg_nb: int
        :returns: registers list or None if fail
        :rtype: list of int or None
        """
        # check params
        if not 0 <= int(reg_addr) <= 0xFFFF:
            raise ValueError("reg_addr out of range (valid from 0 to 65535)")
        if not 1 <= int(reg_nb) <= 125:
            raise ValueError("reg_nb out of range (valid from 1 to 125)")
        if int(reg_addr) + int(reg_nb) > 0x10000:
            raise ValueError("read after end of modbus address space")
        # make request
        try:
            tx_pdu = struct.pack(">BHH", READ_HOLDING_REGISTERS, reg_addr, reg_nb)
            rx_pdu = self._req_pdu(tx_pdu=tx_pdu, rx_min_len=3)
            # extract field "byte count"
            byte_count = rx_pdu[1]
            # frame with regs value
            f_regs = rx_pdu[2:]
            # check rx_byte_count: buffer size must be consistent and have at least the requested number of registers
            if byte_count < 2 * reg_nb or byte_count != len(f_regs):
                raise ModbusClient._NetworkError(MB_RECV_ERR, "rx byte count mismatch")
            # allocate a reg_nb size list
            registers = [0] * reg_nb
            # fill registers list with register items
            for i in range(reg_nb):
                registers[i] = struct.unpack(">H", f_regs[i * 2 : i * 2 + 2])[0]
            # return registers list
            return registers
        # handle error during request
        except ModbusClient._InternalError as e:
            self._req_except_handler(e)
            return None

    def read_input_registers(self, reg_addr, reg_nb=1):
        """Modbus function READ_INPUT_REGISTERS (0x04).

        :param reg_addr: register address (0 to 65535)
        :type reg_addr: int
        :param reg_nb: number of registers to read (1 to 125)
        :type reg_nb: int
        :returns: registers list or None if fail
        :rtype: list of int or None
        """
        # check params
        if not 0 <= int(reg_addr) <= 0xFFFF:
            raise ValueError("reg_addr out of range (valid from 0 to 65535)")
        if not 1 <= int(reg_nb) <= 125:
            raise ValueError("reg_nb out of range (valid from 1 to 125)")
        if int(reg_addr) + int(reg_nb) > 0x10000:
            raise ValueError("read after end of modbus address space")
        # make request
        try:
            tx_pdu = struct.pack(">BHH", READ_INPUT_REGISTERS, reg_addr, reg_nb)
            rx_pdu = self._req_pdu(tx_pdu=tx_pdu, rx_min_len=3)
            # extract field "byte count"
            byte_count = rx_pdu[1]
            # frame with regs value
            f_regs = rx_pdu[2:]
            # check rx_byte_count: buffer size must be consistent and have at least the requested number of registers
            if byte_count < 2 * reg_nb or byte_count != len(f_regs):
                raise ModbusClient._NetworkError(MB_RECV_ERR, "rx byte count mismatch")
            # allocate a reg_nb size list
            registers = [0] * reg_nb
            # fill registers list with register items
            for i in range(reg_nb):
                registers[i] = struct.unpack(">H", f_regs[i * 2 : i * 2 + 2])[0]
            # return registers list
            return registers
        # handle error during request
        except ModbusClient._InternalError as e:
            self._req_except_handler(e)
            return None

    def write_single_coil(self, bit_addr, bit_value):
        """Modbus function WRITE_SINGLE_COIL (0x05).

        :param bit_addr: bit address (0 to 65535)
        :type bit_addr: int
        :param bit_value: bit value to write
        :type bit_value: bool
        :returns: True if write ok
        :rtype: bool
        """
        # check params
        if not 0 <= int(bit_addr) <= 0xFFFF:
            raise ValueError("bit_addr out of range (valid from 0 to 65535)")
        # make request
        try:
            # format "bit value" field for PDU
            bit_value_raw = (0x0000, 0xFF00)[bool(bit_value)]
            # make a request
            tx_pdu = struct.pack(">BHH", WRITE_SINGLE_COIL, bit_addr, bit_value_raw)
            rx_pdu = self._req_pdu(tx_pdu=tx_pdu, rx_min_len=5)
            # decode reply
            resp_coil_addr, resp_coil_value = struct.unpack(">HH", rx_pdu[1:5])
            # check server reply
            if (resp_coil_addr != bit_addr) or (resp_coil_value != bit_value_raw):
                raise ModbusClient._NetworkError(
                    MB_RECV_ERR, "server reply does not match the request"
                )
            return True
        # handle error during request
        except ModbusClient._InternalError as e:
            self._req_except_handler(e)
            return False

    def write_single_register(self, reg_addr, reg_value):
        """Modbus function WRITE_SINGLE_REGISTER (0x06).

        :param reg_addr: register address (0 to 65535)
        :type reg_addr: int
        :param reg_value: register value to write
        :type reg_value: int
        :returns: True if write ok
        :rtype: bool
        """
        # check params
        if not 0 <= int(reg_addr) <= 0xFFFF:
            raise ValueError("reg_addr out of range (valid from 0 to 65535)")
        if not 0 <= int(reg_value) <= 0xFFFF:
            raise ValueError("reg_value out of range (valid from 0 to 65535)")
        # make request
        try:
            # make a request
            tx_pdu = struct.pack(">BHH", WRITE_SINGLE_REGISTER, reg_addr, reg_value)
            rx_pdu = self._req_pdu(tx_pdu=tx_pdu, rx_min_len=5)
            # decode reply
            resp_reg_addr, resp_reg_value = struct.unpack(">HH", rx_pdu[1:5])
            # check server reply
            if (resp_reg_addr != reg_addr) or (resp_reg_value != reg_value):
                raise ModbusClient._NetworkError(
                    MB_RECV_ERR, "server reply does not match the request"
                )
            return True
        # handle error during request
        except ModbusClient._InternalError as e:
            self._req_except_handler(e)
            return False

    def write_multiple_coils(self, bits_addr, bits_value):
        """Modbus function WRITE_MULTIPLE_COILS (0x0F).

        :param bits_addr: bits address (0 to 65535)
        :type bits_addr: int
        :param bits_value: bits values to write
        :type bits_value: list
        :returns: True if write ok
        :rtype: bool
        """
        # check params
        if not 0 <= int(bits_addr) <= 0xFFFF:
            raise ValueError("bit_addr out of range (valid from 0 to 65535)")
        if not 1 <= len(bits_value) <= 1968:
            raise ValueError("number of coils out of range (valid from 1 to 1968)")
        if int(bits_addr) + len(bits_value) > 0x10000:
            raise ValueError("write after end of modbus address space")
        # make request
        try:
            # build PDU coils part
            # allocate a list of bytes
            byte_l = [0] * byte_length(len(bits_value))
            # populate byte list with coils values
            for i, item in enumerate(bits_value):
                if item:
                    byte_l[i // 8] = set_bit(byte_l[i // 8], i % 8)
            # format PDU coils part with byte list
            pdu_coils_part = struct.pack("%dB" % len(byte_l), *byte_l)
            # concatenate PDU parts
            tx_pdu = struct.pack(
                ">BHHB",
                WRITE_MULTIPLE_COILS,
                bits_addr,
                len(bits_value),
                len(pdu_coils_part),
            )
            tx_pdu += pdu_coils_part
            # make a request
            rx_pdu = self._req_pdu(tx_pdu=tx_pdu, rx_min_len=5)
            # response decode
            resp_write_addr, resp_write_count = struct.unpack(">HH", rx_pdu[1:5])
            # check response fields
            write_ok = resp_write_addr == bits_addr and resp_write_count == len(
                bits_value
            )
            return write_ok
        # handle error during request
        except ModbusClient._InternalError as e:
            self._req_except_handler(e)
            return False

    def write_multiple_registers(self, regs_addr, regs_value):
        """Modbus function WRITE_MULTIPLE_REGISTERS (0x10).

        :param regs_addr: registers address (0 to 65535)
        :type regs_addr: int
        :param regs_value: registers values to write
        :type regs_value: list
        :returns: True if write ok
        :rtype: bool
        """
        # check params
        if not 0 <= int(regs_addr) <= 0xFFFF:
            raise ValueError("regs_addr out of range (valid from 0 to 65535)")
        if not 1 <= len(regs_value) <= 123:
            raise ValueError("number of registers out of range (valid from 1 to 123)")
        if int(regs_addr) + len(regs_value) > 0x10000:
            raise ValueError("write after end of modbus address space")
        # make request
        try:
            # init PDU registers part
            pdu_regs_part = b""
            # populate it with register values
            for reg in regs_value:
                # check current register value
                if not 0 <= int(reg) <= 0xFFFF:
                    raise ValueError("regs_value list contains out of range values")
                # pack register for build frame
                pdu_regs_part += struct.pack(">H", reg)
            bytes_nb = len(pdu_regs_part)
            # concatenate PDU parts
            tx_pdu = struct.pack(
                ">BHHB", WRITE_MULTIPLE_REGISTERS, regs_addr, len(regs_value), bytes_nb
            )
            tx_pdu += pdu_regs_part
            # make a request
            rx_pdu = self._req_pdu(tx_pdu=tx_pdu, rx_min_len=5)
            # response decode
            resp_write_addr, resp_write_count = struct.unpack(">HH", rx_pdu[1:5])
            # check response fields
            write_ok = resp_write_addr == regs_addr and resp_write_count == len(
                regs_value
            )
            return write_ok
        # handle error during request
        except ModbusClient._InternalError as e:
            self._req_except_handler(e)
            return False

    def _send(self, frame):
        """Send frame over current socket.

        :param frame: modbus frame to send (MBAP + PDU)
        :type frame: bytes
        """
        # check socket
        if not self.is_open:
            raise ModbusClient._NetworkError(
                MB_SOCK_CLOSE_ERR, "try to send on a close socket"
            )
        # send
        try:
            self._sock.send(frame)
        except socket.timeout:
            self._sock.close()
            raise ModbusClient._NetworkError(MB_TIMEOUT_ERR, "timeout error")
        except socket.error:
            self._sock.close()
            raise ModbusClient._NetworkError(MB_SEND_ERR, "send error")

    def _send_pdu(self, pdu):
        """Convert modbus PDU to frame and send it.

        :param pdu: modbus frame PDU
        :type pdu: bytes
        """
        # for auto_open mode, check TCP and open on need
        if self.auto_open and not self.is_open:
            self._open()
        # add MBAP header to PDU
        tx_frame = self._add_mbap(pdu)
        # send frame with error check
        self._send(tx_frame)
        # debug
        self._debug_dump("Tx", tx_frame)

    def _recv(self, size):
        """Receive data over current socket.

        :param size: number of bytes to receive
        :type size: int
        :returns: receive data or None if error
        :rtype: bytes
        """
        try:
            r_buffer = self._sock.recv(size)
        except socket.timeout:
            self._sock.close()
            raise ModbusClient._NetworkError(MB_TIMEOUT_ERR, "timeout error")
        except socket.error:
            r_buffer = b""
        # handle recv error
        if not r_buffer:
            self._sock.close()
            raise ModbusClient._NetworkError(MB_RECV_ERR, "recv error")
        return r_buffer

    def _recv_all(self, size):
        """Receive data over current socket, loop until all bytes is received (avoid TCP frag).

        :param size: number of bytes to receive
        :type size: int
        :returns: receive data or None if error
        :rtype: bytes
        """
        r_buffer = b""
        while len(r_buffer) < size:
            r_buffer += self._recv(size - len(r_buffer))
        return r_buffer

    def _recv_pdu(self, min_len=2):
        """Receive the modbus PDU (Protocol Data Unit).

        :param min_len: minimal length of the PDU
        :type min_len: int
        :returns: modbus frame PDU or None if error
        :rtype: bytes or None
        """
        # receive 7 bytes header (MBAP)
        rx_mbap = self._recv_all(7)
        # decode MBAP
        (f_transaction_id, f_protocol_id, f_length, f_unit_id) = struct.unpack(
            ">HHHB", rx_mbap
        )
        # check MBAP fields
        f_transaction_err = f_transaction_id != self._transaction_id
        f_protocol_err = f_protocol_id != 0
        f_length_err = f_length >= 256
        f_unit_id_err = f_unit_id != self.unit_id
        # checking error status of fields
        if f_transaction_err or f_protocol_err or f_length_err or f_unit_id_err:
            self.close()
            self._debug_dump("Rx", rx_mbap)
            raise ModbusClient._NetworkError(MB_RECV_ERR, "MBAP checking error")
        # recv PDU
        rx_pdu = self._recv_all(f_length - 1)
        # for auto_close mode, close socket after each request
        if self.auto_close:
            self.close()
        # dump frame
        self._debug_dump("Rx", rx_mbap + rx_pdu)
        # body decode
        # check PDU length for global minimal frame (an except frame: func code + exp code)
        if len(rx_pdu) < 2:
            raise ModbusClient._NetworkError(MB_RECV_ERR, "PDU length is too short")
        # extract function code
        rx_fc = rx_pdu[0]
        # check except status
        if rx_fc >= 0x80:
            exp_code = rx_pdu[1]
            raise ModbusClient._ModbusExcept(exp_code)
        # check PDU length for specific request set in min_len (keep this after except checking)
        if len(rx_pdu) < min_len:
            raise ModbusClient._NetworkError(
                MB_RECV_ERR, "PDU length is too short for current request"
            )
        # if no error, return PDU
        return rx_pdu

    def _add_mbap(self, pdu):
        """Return full modbus frame with MBAP (modbus application protocol header) append to PDU.

        :param pdu: modbus PDU (protocol data unit)
        :type pdu: bytes
        :returns: full modbus frame
        :rtype: bytes
        """
        # build MBAP
        self._transaction_id = random.randint(0, 65535)
        protocol_id = 0
        length = len(pdu) + 1
        mbap = struct.pack(
            ">HHHB", self._transaction_id, protocol_id, length, self.unit_id
        )
        # full modbus/TCP frame = [MBAP]PDU
        return mbap + pdu

    def _req_pdu(self, tx_pdu, rx_min_len=2):
        """Request processing (send and recv PDU).

        :param tx_pdu: modbus PDU (protocol data unit) to send
        :type tx_pdu: bytes
        :param rx_min_len: min length of receive PDU
        :type rx_min_len: int
        :returns: the receive PDU or None if error
        :rtype: bytes
        """
        # init request engine
        self._req_init()
        # send PDU
        self._send_pdu(tx_pdu)
        # return receive PDU
        return self._recv_pdu(min_len=rx_min_len)

    def _req_init(self):
        """Reset request status flags."""
        self._last_error = MB_NO_ERR
        self._last_except = EXP_NONE

    def _req_except_handler(self, _except):
        """Global handler for internal exceptions."""
        # on request network error
        if isinstance(_except, ModbusClient._NetworkError):
            self._last_error = _except.code
            self._debug_msg(_except.message)
        # on request modbus except
        if isinstance(_except, ModbusClient._ModbusExcept):
            self._last_error = MB_EXCEPT_ERR
            self._last_except = _except.code
            self._debug_msg(
                'modbus exception (code %d "%s")'
                % (self.last_except, self.last_except_as_txt)
            )

    def _debug_msg(self, msg):
        """Print debug message if debug mode is on.

        :param msg: debug message
        :type msg: str
        """
        if self.debug:
            print(msg)

    def _debug_dump(self, label, frame):
        """Print debug dump if debug mode is on.

        :param label: head label
        :type label: str
        :param frame: modbus frame
        :type frame: bytes
        """
        if self.debug:
            self._pretty_dump(label, frame)

    @staticmethod
    def _pretty_dump(label, frame):
        """Dump a modbus frame.

        modbus/TCP format: [MBAP] PDU

        :param label: head label
        :type label: str
        :param frame: modbus frame
        :type frame: bytes
        """
        # split data string items to a list of hex value
        dump = ["%02X" % c for c in frame]
        # format message
        dump_mbap = " ".join(dump[0:7])
        dump_pdu = " ".join(dump[7:])
        msg = "[%s] %s" % (dump_mbap, dump_pdu)
        # print result
        print(label)
        print(msg)


""" pyModbusTCP Client """
