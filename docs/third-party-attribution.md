# License and third-party attribution

The root files have separate purposes:

| File | Applies to | Copyright notice |
| --- | --- | --- |
| [LICENSE](../LICENSE) | ShadeCheck's original code and documentation | 2026 Aje Oluwaseun Isaac (0xaje) |
| [THIRD_PARTY_LICENSE](../THIRD_PARTY_LICENSE) | Vendored lightwalletd protocol material | 2019 Electric Coin Company |

Both contain MIT terms because the original project and the upstream material use that license. Keep both notices when redistributing the relevant material. The upstream copyright has not been replaced with the project author's name.

The vendored `proto/service.proto` and `proto/compact_formats.proto` come from [zcash/lightwalletd](https://github.com/zcash/lightwalletd) revision `d16d48124e9ad4157ebc2324b5090c6ba201470c`. Generated Python protocol stubs derive from that schema. [Fixture provenance](../fixtures/PROVENANCE.md) records the source and boundaries of the serialization fixture.

Zcash node images, lightwalletd, Zingo, and installed dependencies remain separate upstream software with their own notices and license terms. ShadeCheck's MIT license does not replace those terms. The Zingo example includes recorded integration evidence and reproduction instructions, not a relicensed copy of its source or binary.
