

def get_vms(name: str):
    if 'guibot_simple' == name:
        from .third_party import GuibotSimpleVm
        return GuibotSimpleVm

