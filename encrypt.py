import dotbot

''' TODO just something things to remember
- encrypt should print the files it sees (for validation purposes)


'''


# TODO might have to split encrypt and decrypt into their own worker classes
class Encrypt(dotbot.Plugin):
    DIRECTIVE_ENCRYPT = 'encrypt'
    DIRECTIVE_DECRYPT = 'decrypt'

    def can_handle(self, directive):
        return directive in [self.DIRECTIVE_DECRYPT, self.DIRECTIVE_ENCRYPT]
    
    def handle(self, directive, data):
        if directive == self.DIRECTIVE_DECRYPT:
            return self._handle_decrypt(data)
        elif directive == self.DIRECTIVE_ENCRYPT:
            return self._handle_encrypt(data)
        else:
            raise ValueError('Encrypt cannot handle directive %s' % directive)
    
    def _handle_decrypt(self, data):
        self._log.error("Encrypt: decrypt not implemented.")
        return False

    def _handle_encrypt(self, data):
        self._log.error("Encrypt: encrypt not implemented.")
        return False