import yaml
import os
import glob
from common.logger import setup_logger

logger = setup_logger(__name__)

class InvalidConfigurationError(Exception):
    """Raised when an ECU configuration file violates the schema."""
    pass

def load_ecu_configs(config_dir: str) -> list[dict]:
    """
    Load and validate all YAML ECU configuration files from a directory.
    
    :param config_dir: Path to the directory containing .yaml config files.
    :return: List of validated dictionary configurations.
    """
    configs = []
    
    if not os.path.exists(config_dir):
        logger.warning(f"Configuration directory {config_dir} does not exist.")
        return configs
        
    yaml_files = glob.glob(os.path.join(config_dir, "*.yaml"))
    
    for file_path in yaml_files:
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
                
            validate_ecu_config(config, file_path)
            configs.append(config)
            logger.info(f"Loaded valid configuration for {config['name']} from {os.path.basename(file_path)}")
        except InvalidConfigurationError as e:
            logger.error(f"Schema validation failed for {file_path}: {e}")
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            
    return configs

def validate_ecu_config(config: dict, source: str):
    """
    Validate the dictionary schema matches the required ECU configuration format.
    """
    if not isinstance(config, dict):
        raise InvalidConfigurationError("Root element must be a dictionary.")
        
    required_keys = ['name', 'logical_address', 'vin', 'supported_services', 'data_identifiers']
    for key in required_keys:
        if key not in config:
            raise InvalidConfigurationError(f"Missing required key: '{key}'")
            
    if not isinstance(config['name'], str):
        raise InvalidConfigurationError("'name' must be a string.")
        
    if not isinstance(config['logical_address'], int):
        # Allow hex strings or ints
        if isinstance(config['logical_address'], str) and config['logical_address'].startswith("0x"):
            config['logical_address'] = int(config['logical_address'], 16)
        else:
            raise InvalidConfigurationError("'logical_address' must be an integer or hex string.")
            
    if not isinstance(config['vin'], str) or len(config['vin']) != 17:
        raise InvalidConfigurationError("'vin' must be exactly a 17 character string.")
        
    if not isinstance(config['supported_services'], list):
        raise InvalidConfigurationError("'supported_services' must be a list of integers.")
        
    if not isinstance(config['data_identifiers'], dict):
        raise InvalidConfigurationError("'data_identifiers' must be a dictionary.")
