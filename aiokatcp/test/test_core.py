import enum
import json
import ipaddress
import unittest
import unittest.mock

from aiokatcp.core import (
    Message, KatcpSyntaxError, Address, Timestamp, encode, decode, register_type, get_type)


class MyEnum(enum.Enum):
    BATMAN = 1
    JOKER = 2
    TWO_FACE = 3


class OverrideEnum(enum.Enum):
    BATMAN = b'cheese'
    JOKER = b'carrot'
    TWO_FACE = b'apple'

    def __init__(self, value):
        self.katcp_value = value


class TestAddress(unittest.TestCase):
    def setUp(self):
        self.v4_no_port = Address(ipaddress.ip_address('127.0.0.1'))
        self.v4_port = Address(ipaddress.ip_address('127.0.0.1'), 7148)
        self.v6_no_port = Address(ipaddress.ip_address('::1'))
        self.v6_port = Address(ipaddress.ip_address('::1'), 7148)
        self.v6_port_alt = Address(ipaddress.ip_address('00:00::1'), 7148)

    def test_eq(self):
        for addr in [self.v4_no_port, self.v4_port, self.v6_no_port, self.v6_port]:
            self.assertTrue(addr == addr)
        self.assertTrue(self.v6_port == self.v6_port_alt)
        self.assertFalse(self.v4_no_port == self.v4_port)
        self.assertFalse(self.v4_port == self.v6_port)
        self.assertFalse(self.v4_no_port == '127.0.0.1')

    def test_not_eq(self):
        self.assertFalse(self.v6_port != self.v6_port_alt)
        self.assertTrue(self.v4_no_port != self.v4_port)
        self.assertTrue(self.v4_no_port != self.v6_no_port)
        self.assertTrue(self.v4_no_port != '127.0.0.1')

    def test_str(self):
        self.assertEqual(str(self.v4_no_port), '127.0.0.1')
        self.assertEqual(str(self.v4_port), '127.0.0.1:7148')
        self.assertEqual(str(self.v6_no_port), '[::1]')
        self.assertEqual(str(self.v6_port), '[::1]:7148')

    def test_bytes(self):
        self.assertEqual(bytes(self.v4_no_port), b'127.0.0.1')
        self.assertEqual(bytes(self.v4_port), b'127.0.0.1:7148')
        self.assertEqual(bytes(self.v6_no_port), b'[::1]')
        self.assertEqual(bytes(self.v6_port), b'[::1]:7148')

    def test_repr(self):
        self.assertEqual(repr(self.v4_no_port), "Address(IPv4Address('127.0.0.1'))")
        self.assertEqual(repr(self.v4_port), "Address(IPv4Address('127.0.0.1'), 7148)")
        self.assertEqual(repr(self.v6_no_port), "Address(IPv6Address('::1'))")
        self.assertEqual(repr(self.v6_port), "Address(IPv6Address('::1'), 7148)")

    def test_hash(self):
        self.assertEqual(hash(self.v6_port), hash(self.v6_port_alt))
        self.assertNotEqual(hash(self.v4_port), hash(self.v4_no_port))
        self.assertNotEqual(hash(self.v4_port), hash(self.v6_port))

    def test_parse(self):
        for addr in [self.v4_no_port, self.v4_port, self.v6_no_port, self.v6_port]:
            self.assertEqual(Address.parse(bytes(addr)), addr)
        self.assertRaises(ValueError, Address.parse, b'')
        self.assertRaises(ValueError, Address.parse, b'[127.0.0.1]')
        self.assertRaises(ValueError, Address.parse, b'::1')


class TestEncodeDecode(unittest.TestCase):
    VALUES = [
        (str, 'café', b'caf\xc3\xa9'),
        (bytes, b'caf\xc3\xa9', b'caf\xc3\xa9'),
        (int, 123, b'123'),
        (bool, True, b'1'),
        (bool, False, b'0'),
        (float, -123.5, b'-123.5'),
        (float, 1e+20, b'1e+20'),
        (Timestamp, Timestamp(123.5), b'123.5'),
        (Address, Address(ipaddress.ip_address('127.0.0.1')), b'127.0.0.1'),
        (MyEnum, MyEnum.TWO_FACE, b'two-face'),
        (OverrideEnum, OverrideEnum.JOKER, b'carrot')
    ]

    BAD_VALUES = [
        (str, b'caf\xc3e'),      # Bad unicode
        (bool, b'2'),
        (int, b'123.0'),
        (float, b''),
        (Address, b'[127.0.0.1]'),
        (MyEnum, b'two_face'),
        (MyEnum, b'TWO-FACE'),
        (OverrideEnum, b'joker')
    ]

    def test_encode(self):
        for _, value, raw in self.VALUES:
            self.assertEqual(encode(value), raw)

    def test_decode(self):
        for type_, value, raw in self.VALUES:
            self.assertEqual(decode(type_, raw), value)

    def test_unknown_class(self):
        self.assertRaises(TypeError, decode, dict, b'{"test": "it"}')

    def test_bad_raw(self):
        for type_, value in self.BAD_VALUES:
            with self.assertRaises(ValueError,
                                   msg='{} should not be valid for {}'.format(value, type_)):
                decode(type_, value)

    @unittest.mock.patch.dict('aiokatcp.core._types')
    def test_register_type(self):
        register_type(
            dict, 'string',
            lambda value: json.dumps(value, sort_keys=True).encode('utf-8'),
            lambda cls, value: cls(json.loads(value.decode('utf-8'))))
        value = {"h": 1, "i": [2]}
        raw = b'{"h": 1, "i": [2]}'
        self.assertEqual(encode(value), raw)
        self.assertEqual(decode(dict, raw), value)
        self.assertRaises(ValueError, decode, dict, b'"string"')
        self.assertRaises(ValueError, decode, dict, b'{missing_quotes: 1}')
        # Try re-registering for an already registered type
        with self.assertRaises(ValueError):
            register_type(
                dict, 'string',
                lambda value: json.dumps(value, sort_keys=True).encode('utf-8'),
                lambda cls, value: cls(json.loads(value.decode('utf-8'))))

    def test_default(self):
        self.assertEqual(get_type(int).default(int), 0)
        self.assertEqual(get_type(float).default(float), 0.0)
        self.assertEqual(get_type(str).default(str), '')
        self.assertEqual(get_type(bytes).default(bytes), b'')
        self.assertEqual(get_type(Timestamp).default(Timestamp), Timestamp(0.0))
        self.assertEqual(get_type(MyEnum).default(MyEnum), MyEnum.BATMAN)
        self.assertEqual(get_type(OverrideEnum).default(OverrideEnum), OverrideEnum.BATMAN)


class TestMessage(unittest.TestCase):
    def test_init_basic(self):
        msg = Message(Message.Type.REQUEST,
                      'hello', 'world', b'binary\xff\x00', 123, 234.5, True, False)
        self.assertEqual(msg.mtype, Message.Type.REQUEST)
        self.assertEqual(msg.name, 'hello')
        self.assertEqual(msg.arguments, [
            b'world', b'binary\xff\x00', b'123', b'234.5', b'1', b'0'])
        self.assertIsNone(msg.mid)

    def test_init_mid(self):
        msg = Message(Message.Type.REPLY, 'hello', 'world', mid=345)
        self.assertEqual(msg.mtype, Message.Type.REPLY)
        self.assertEqual(msg.name, 'hello')
        self.assertEqual(msg.arguments, [b'world'])
        self.assertEqual(msg.mid, 345)

    def test_init_bad_name(self):
        self.assertRaises(ValueError, Message, Message.Type.REPLY,
                          'underscores_bad', 'world', mid=345)
        self.assertRaises(ValueError, Message, Message.Type.REPLY,
                          '', 'world', mid=345)
        self.assertRaises(ValueError, Message, Message.Type.REPLY,
                          '1numberfirst', 'world', mid=345)

    def test_init_bad_mid(self):
        self.assertRaises(ValueError, Message, Message.Type.REPLY,
                          'hello', 'world', mid=0)
        self.assertRaises(ValueError, Message, Message.Type.REPLY,
                          'hello', 'world', mid=0x1000000000)

    def test_request(self):
        msg = Message.request('hello', 'world')
        self.assertEqual(msg.mtype, Message.Type.REQUEST)
        self.assertEqual(msg.name, 'hello')
        self.assertEqual(msg.arguments, [b'world'])
        self.assertIsNone(msg.mid)

    def test_reply(self):
        msg = Message.reply('hello', 'world', mid=None)
        self.assertEqual(msg.mtype, Message.Type.REPLY)
        self.assertEqual(msg.name, 'hello')
        self.assertEqual(msg.arguments, [b'world'])
        self.assertIsNone(msg.mid)

    def test_inform(self):
        msg = Message.inform('hello', 'world', mid=1)
        self.assertEqual(msg.mtype, Message.Type.INFORM)
        self.assertEqual(msg.name, 'hello')
        self.assertEqual(msg.arguments, [b'world'])
        self.assertEqual(msg.mid, 1)

    def test_reply_to_request(self):
        req = Message.request('hello', 'world', mid=1)
        reply = Message.reply_to_request(req, 'test')
        self.assertEqual(reply.mtype, Message.Type.REPLY)
        self.assertEqual(reply.name, 'hello')
        self.assertEqual(reply.arguments, [b'test'])
        self.assertEqual(reply.mid, 1)

    def test_inform_reply(self):
        req = Message.request('hello', 'world', mid=1)
        reply = Message.inform_reply(req, 'test')
        self.assertEqual(reply.mtype, Message.Type.INFORM)
        self.assertEqual(reply.name, 'hello')
        self.assertEqual(reply.arguments, [b'test'])
        self.assertEqual(reply.mid, 1)

    def test_bytes(self):
        msg = Message.request(
            'hello', 'café', b'_bin ary\xff\x00\n\r\t\\\x1b', 123, 234.5, True, False, '')
        raw = bytes(msg)
        expected = b'?hello caf\xc3\xa9 _bin\\_ary\xff\\0\\n\\r\\t\\\\\\e 123 234.5 1 0 \\@\n'
        self.assertEqual(raw, expected)

    def test_bytes_mid(self):
        msg = Message.reply('fail', 'on fire', mid=234)
        self.assertEqual(bytes(msg), b'!fail[234] on\\_fire\n')

    def test_parse(self):
        msg = Message.parse(b'?test message \\0\\n\\r\\t\\e\\_binary\n')
        self.assertEqual(msg, Message.request('test', 'message', b'\0\n\r\t\x1b binary'))

    def test_parse_mid(self):
        msg = Message.parse(b'?test[222] message \\0\\n\\r\\t\\e\\_binary\n')
        self.assertEqual(msg, Message.request('test', 'message', b'\0\n\r\t\x1b binary', mid=222))
        msg = Message.parse(b'?test[1] message\n')
        self.assertEqual(msg, Message.request('test', 'message', mid=1))

    def test_parse_empty(self):
        self.assertRaises(KatcpSyntaxError, Message.parse, b'')

    def test_parse_leading_whitespace(self):
        self.assertRaises(KatcpSyntaxError, Message.parse, b' !ok\n')

    def test_parse_bad_name(self):
        self.assertRaises(KatcpSyntaxError, Message.parse, b'?bad_name message\n')
        self.assertRaises(KatcpSyntaxError, Message.parse, b'? emptyname\n')

    def test_parse_out_of_range_mid(self):
        self.assertRaises(KatcpSyntaxError, Message.parse, b'!ok[1000000000000]\n')

    def test_parse_bad_mid(self):
        self.assertRaises(KatcpSyntaxError, Message.parse, b'!ok[10\n')
        self.assertRaises(KatcpSyntaxError, Message.parse, b'!ok[0]\n')
        self.assertRaises(KatcpSyntaxError, Message.parse, b'!ok[a]\n')

    def test_parse_bad_type(self):
        self.assertRaises(KatcpSyntaxError, Message.parse, b'%ok\n')

    def test_parse_bad_escape(self):
        self.assertRaises(KatcpSyntaxError, Message.parse, b'!ok \\q\n')
        self.assertRaises(KatcpSyntaxError, Message.parse, b'!ok q\\ other\n')

    def test_parse_unescaped(self):
        self.assertRaises(KatcpSyntaxError, Message.parse, b'!ok \x1b\n')

    def test_parse_no_newline(self):
        self.assertRaises(KatcpSyntaxError, Message.parse, b'!ok')

    def test_compare(self):
        a = Message.request('info', 'yes')
        a2 = Message.request('info', 'yes')
        b = Message.request('info', 'yes', mid=123)
        c = Message.request('info', 'no')
        d = Message.request('other', 'yes')
        e = Message.reply('info', 'yes')
        f = 5
        for other in [b, c, d, e, f]:
            self.assertTrue(a != other)
            self.assertFalse(a == other)
            self.assertNotEqual(hash(a), hash(other))
        self.assertTrue(a == a2)
        self.assertEqual(hash(a), hash(a2))

    def test_reply_ok(self):
        self.assertTrue(Message.reply('query', 'ok').reply_ok())
        self.assertFalse(Message.reply('query', 'fail', 'error').reply_ok())
        self.assertFalse(Message.request('query', 'ok').reply_ok())
