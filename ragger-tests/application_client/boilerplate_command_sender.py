from enum import IntEnum
from typing import Generator, List, Optional, Tuple
from contextlib import contextmanager
from typing import Dict
from hashlib import sha256
from struct import unpack

from ragger.backend.interface import BackendInterface, RAPDU
from bip_utils import Bip32Utils


MAX_APDU_LEN: int = 255

CLA: int = 0x00

class P1(IntEnum):
    # Parameter 1 for first APDU number.
    P1_START = 0x00
    # Parameter 1 for maximum APDU number.
    P1_MAX   = 0x03
    # Parameter 1 for screen confirmation for GET_PUBLIC_KEY.
    P1_CONFIRM = 0x01

class P2(IntEnum):
    # Parameter 2 for last APDU to receive.
    P2_LAST = 0x00
    # Parameter 2 for more APDU to receive.
    P2_MORE = 0x00

class InsType(IntEnum):
    GET_VERSION    = 0x00
    GET_APP_NAME   = 0x00
    VERIFY_ADDRESS = 0x01
    GET_PUBLIC_KEY = 0x02
    SIGN_TX        = 0x03

class Errors(IntEnum):
    SW_DENY                    = 0x6985
    SW_WRONG_P1P2              = 0x6A86
    SW_INS_NOT_SUPPORTED       = 0x6D00
    SW_CLA_NOT_SUPPORTED       = 0x6E00
    SW_WRONG_APDU_LENGTH       = 0x6E03
    SW_WRONG_RESPONSE_LENGTH   = 0xB000
    SW_DISPLAY_BIP32_PATH_FAIL = 0xB001
    SW_DISPLAY_ADDRESS_FAIL    = 0xB002
    SW_DISPLAY_AMOUNT_FAIL     = 0xB003
    SW_WRONG_TX_LENGTH         = 0xB004
    SW_TX_PARSING_FAIL         = 0xB005
    SW_TX_HASH_FAIL            = 0xB006
    SW_BAD_STATE               = 0xB007
    SW_SIGNATURE_FAIL          = 0xB008


def split_message(message: bytes, max_size: int) -> List[bytes]:
    return [message[x:x + max_size] for x in range(0, len(message), max_size)]


class BoilerplateCommandSender:
    def __init__(self, backend: BackendInterface) -> None:
        self.backend = backend
        self.send_fn = self.send_chunks

    def set_use_block_protocol(self, v):
        if v:
            self.send_fn = self.send_chunks
        else:
            self.send_fn = self.send_with_blocks

    def get_app_and_version(self) -> Tuple[Tuple[int, int, int], str]:
        response = self.send_fn(cla=CLA,
                            ins=InsType.GET_VERSION,
                            p1=P1.P1_START,
                            p2=P2.P2_LAST,
                            payload=b"")
        print(response)
        major, minor, patch = unpack("BBB", response[:3])
        return ((major, minor, patch), response[3:].decode("ascii"))

    def get_public_key(self, path: str) -> Tuple[int, bytes, int, bytes]:
        return self.get_public_key_impl(InsType.GET_PUBLIC_KEY, path)

    def get_public_key_with_confirmation(self, path: str) -> Tuple[int, bytes, int, bytes]:
        return self.get_public_key_impl(InsType.VERIFY_ADDRESS, path)


    def get_public_key_impl(self, ins, path: str) -> Tuple[int, bytes, int, bytes]:
        response = self.send_fn(cla=CLA,
                                ins=ins,
                                p1=P1.P1_START,
                                p2=P2.P2_LAST,
                                payload=pack_derivation_path(path))
        response, pub_key_len, pub_key = pop_size_prefixed_buf_from_buf(response)
        response, chain_code_len, chain_code = pop_size_prefixed_buf_from_buf(response)
        return pub_key_len, pub_key, chain_code_len, chain_code


    @contextmanager
    def sign_tx(self, path: str, transaction: bytes) -> Generator[None, None, None]:
        print ("started sign_tx")
        tx_len = (len(transaction)).to_bytes(4, byteorder='little')
        payload = tx_len + transaction + pack_derivation_path(path)
        return self.send_fn(cla=CLA,
                     ins=InsType.SIGN_TX,
                     p1=P1.P1_START,
                     p2=P2.P2_LAST,
                     payload=payload)
        # with self.send_fn(cla=CLA,
        #                       ins=InsType.SIGN_TX,
        #                       p1=P1.P1_START,
        #                       p2=P2.P2_LAST,
        #                       payload=payload) as response:
        #     print ("before sign_tx yield")
        #     yield response

    def get_async_response(self) -> Optional[RAPDU]:
        return self.backend.last_async_response

    def send_chunks(self, cla, ins, p1, p2, payload: bytes) -> bytes:
        messages = split_message(payload, MAX_APDU_LEN)
        if messages == []:
            messages = [b'']

        result = b''
        print(f"send_chunks {messages}")

        for msg in messages:
            print(f"send_chunks {msg}")
            # with self.backend.exchange_async(cla=cla,
            #                                ins=ins,
            #                                p1=p1,
            #                                p2=p2,
            #                                data=msg) as resp:
            # rapdu = self.backend.exchange(cla=cla,
            #                                ins=ins,
            #                                p1=p1,
            #                                p2=p2,
            #                                data=msg)
            self.backend.exchange(cla=cla,
                                           ins=ins,
                                           p1=p1,
                                           p2=p2,
                                           data=msg)
            print(f"after exchange {msg}")
            # rv = rapdu.data
            # print(f"send_chunks got rv {rv}")
            # result = rv

        return result


    # Block Protocol
    def send_with_blocks(self, cla, ins, p1, p2, payload: bytes, extra_data: Dict[str, bytes]) -> bytes:
        chunk_size = 180
        parameter_list = []

        if not isinstance(payload, list):
            payload = [payload]

        data = {}

        if extra_data:
            data.update(extra_data)

        for item in payload:
            chunk_list = []
            for i in range(0, len(item), chunk_size):
                chunk = item[i:i + chunk_size]
                chunk_list.append(chunk)

            last_hash = b'\x00' * 32

            for chunk in reversed(chunk_list):
                linked_chunk = last_hash + chunk
                last_hash = sha256(linked_chunk)
                data[last_hash.hex()] = linked_chunk

            parameter_list.append(last_hash)

        initialPayload = HostToLedger.START.to_bytes(1) + parameter_list, data

        return self.handle_block_protocol(cla, ins, p1, p2, initialPayload, data)

    # def handle_block_protocol(self, cla, ins, p1, p2, initialPayload: bytes, data: Dict[str, bytes]) -> bytes:
    #     payload = initialPayload
    #     rv_instruction = -1
    #     result: bytes

    #     while (rv_instruction != LedgerToHost.RESULT_FINAL):
    #         rv = self.backend.exchange(cla=cla,
    #                                  ins=ins,
    #                                  p1=p1,
    #                                  p2=p2,
    #                                  data=payload)
    #         print("Received response")
    #         rv_instruction = rv[0]
    #         rv_payload = rv[1:-2]

    #         match rv_instruction:
    #             case LedgerToHost.RESULT_ACCUMULATING:
    #                 result = result + rv_payload
    #                 payload = HostToLedger.RESULT_ACCUMULATING_RESPONSE.to_bytes(1)
    #             case LedgerToHost.RESULT_FINAL:
    #                 result = result + rv_payload
    #             case LedgerToHost.GET_CHUNK:
    #                 chunk_hash = rv_payload.hex()
    #                 if chunk_hash in data:
    #                     chunk = data[rv_payload.hex()]
    #                     payload = HostToLedger.GET_CHUNK_RESPONSE_SUCCESS.to_bytes(1) + chunk
    #                 else:
    #                     payload = HostToLedger.GET_CHUNK_RESPONSE_FAILURE.to_bytes(1)
    #             case LedgerToHost.PUT_CHUNK:
    #                 data[sha256(rv_payload).hexdigest()] = rv_payload
    #                 payload = HostToLedger.PUT_CHUNK_RESPONSE.to_bytes(1)
    #             case _:
    #                 raise RuntimeError "Unknown instruction returned from ledger"

    #     return result

class LedgerToHost(IntEnum):
    RESULT_ACCUMULATING = 0
    RESULT_FINAL = 1
    GET_CHUNK = 2
    PUT_CHUNK = 3

class HostToLedger(IntEnum):
    START = 0
    GET_CHUNK_RESPONSE_SUCCESS = 1
    GET_CHUNK_RESPONSE_FAILURE = 2
    PUT_CHUNK_RESPONSE = 3
    RESULT_ACCUMULATING_RESPONSE = 4

def pack_derivation_path(derivation_path: str) -> bytes:
    split = derivation_path.split("/")

    if split[0] != "m":
        raise ValueError("Error master expected")

    path_bytes: bytes = (len(split) - 1).to_bytes(1, byteorder='little')
    for value in split[1:]:
        if value == "":
            raise ValueError(f'Error missing value in split list "{split}"')
        if value.endswith('\''):
            path_bytes += Bip32Utils.HardenIndex(int(value[:-1])).to_bytes(4, byteorder='little')
        else:
            path_bytes += int(value).to_bytes(4, byteorder='little')
    return path_bytes
