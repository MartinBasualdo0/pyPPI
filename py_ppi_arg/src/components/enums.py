from enum import Enum

class InstrumentType(Enum):
     """Enumerates the instruments categories in the application."""
     
     CORPORATE = "140"
     PUBLIC_BOND = "100"
     LETRAS = "110"

class Settlement(Enum):
    """Enumerates the settlement options for trades in the application."""
    
    T0 = "1" #"CI"
    T1 = "2" #"24hs"
    T2 = "3" #the same as T1 
    T3 = "4" #the same as T1
    
class OperationType(Enum):
    
    COMPRA = "10000"
    OTRO = "10040"
    
class Currency(Enum):
    
    USD = "10001"