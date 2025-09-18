#!/usr/bin/env python
"""
Move existing RFP folders to the Daily Run RFPs folder
"""

import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Extract folder IDs from the URLs provided
folder_ids = [
    '1VBxrQ50Yi-lQ1kbecBaWv147r4K-L57d',
    '1R1-FOPA9_FuSjm69XMOoKsKEaiC3gpLZ',
    '1AYjyjwOw0ZL0xjSouiIOti3IrU_R3XiV',
    '14mlQGyKRERqzJ1mqDUyJ42jupeuTUPQX',
    '1Ycqz0oVL9iOhmLiFUFCx4nA3zGuHsGdF',
    '1TYlBorpQbQmuW7bGaCp_Ol8VfJHUphTl',
    '1M2nPrSdowrbZf51Y5No3ayaDGeBuSJdu',
    '1PUDo7Yn9OS96w_dPU3czdb8nlhm9Sk4J',
    '1CtASGMuYmPu60t9mP4s9TpjUHEh1MAAm',
    '18WAAYXZHKFTOIxDj05K6W39gfagVfUdP',
    '1ZeOb-WT7Km6LlnflA3VfcEhW2E1qxPYf',
    '10DbHCdsEbi5qBqsYTomNcmi5J2siffpH',
    '1epZoIH9ORLA5IsfSY-gOkPZ3IAYHPfIC',
    # '1RtnSg3tEU-BzI8UOCqL2zUZDBSvT2CdA',  # MERCURY - EXCLUDED
    '1Y4SHcCwUkxIscBiJ6-vSdULhzt4Lfrj8',
    '1Dso3oZC2b9bVSq1cUDkJ0P5gbt35mUD3',
    '11vLxoPVkzS3zvEAT-u4Byn0ETg-jZobG',
    '10EBPYz98KQSNhgUGdVcXgZ_Ju1EUQwEG',
    '1QE1IpHnDcCmnP49lMYHGofqb5-Iv7vS4',
    '1eGGvoCfF5Z-ewjyWm0fqRJ-oNUbOau7p',
    '115AsR7qfrTHr-3tz7q_LJiuMmldWNhvT',
    '18GeGPGvxMEcge8byOGMjxgVGmFZCVU_4',
    '1do3aLMcqYMnOEFnoVSv0cs2RumRet_5V',
    '1OH6CacLO_lZR0SSKymPuYo9iOgTLX-2U',
    '1yQeu7fMbjWaceI-0D8qN-XDj0z9MdOSi',
    '1rCLH2mwMPUxAER6T7i9tehP_i_2q2Wiq',
    '18-Idbcu-pVin6sYWRvUwmhp0z5E9d-_J',
    '146nZlgRJOaSU9QWSo0xFXb_uzKU3iNlx',
    '1oNhsUZJ1kfusScsqfMcQUk65ZphPfx5Y',
    '1_5IKbngwIjFnA6jNYel48BvOb0S2SexO',
    '112d_51qozfS0h-5vodRYsoIx-9d2tKu0',
    '1Cgf4J4QnWBLV7fC2Zp1TzBwNipm0qtNP',
    '1SCKHjeZ51fEWKsTFn75Rx-6dXc2t-ycO',
    '1IeLDohqbxqEQbel350my_s18F_CuY6wi',
    '1OWkOlqyCWLvOSW9gi47kiUoU0C10WwAs',
    '1NjVVPNmyK1CR2Ws68aoPfAjxHjjX9I26',
    '1O_U45AxVx0UIaug8ABmXH062FQg_b4ej',
    '19XMcRz37b7QoeKj0opEAWXAaleVI-WRN',
    '1q_mhu8CzWcfviPZPul824D-e1Vt_HSGu',
    '1tR9M4oy0eFII1RcPOXBtXrU5M0XUuMUs',
    '1msYF0b08mCeojEPL_Kc9fI76yrYWneGf',
    '16Mqi-3JoT1oJ7BTxhVzZYv9_6NoXr8zI',
    '1avBzfL-WqEFVySOKzoBo6eIM1xrjgDlF',
    '1VGVJJxL824DAmZP0akWxcEDhZyi3IKOG',
    '1xO2vwel3DvDMhxDtgI6ZvjVdsD9tcPzT',
    '1xS3nUuALAtv5H3DpdFNxi1b8ShKD1RwM',
    '1BBKwJs-spqYIWGB4HsGF6pR2-CF3U3BG',
    '1fZ15NvwXXaoOUx6M_4Gfs5AcgM7u9WNu',
    '1EYLagJIEHli1XAZ5_ZaYeQXJ1kZkbPYS',
    '1io8RKpidbnVq0SFkVcDsLhYlbW8m6skG',
    '1WMMhe9WD2RFd-jeYFf8O8LOm61JC_x3N',
    '1CCRgQasxU9_U5bVWKLN75OFT4dPLtLv0',
    '1ceKAEKfBD5u-l7STrDSpgrK8wUsZN47C',
    '1AgkfD6MIKQlNW8gVk4zmFDcx4m1fbKJv',
    '1M8zB8mCQNDeDMzzoVrcPLwvSniaXQ_2w',
    '1WflMQQ2GJB9JiMI0f2DkRIHWbgNUzM0V',
    '14lIkSJAtPsm5WQphneR2E9_pLz_l4HBi',
    '1hDR7gpWk6zFAv1LvgRw1MpKXA5UNNecK',
    '1LzOYO0kkXoRXuGvOxF7nsT-c1dWlRCXr',
    '1kPh8CONlCHIJEx1QKqNyCyb8b0bzjiZn',
    '1N2o6nrJa45uW7NIVJtdbqzUw-MctC80m',
    '1Phai3bT_i_z-rNGRMCMXG9hrhes9w4tM',
    '1Tc7UJjk_Z38bn0hii10wkPTShT3B1Nqz',
    '1ie8mwpjMXczYbzw0jKu1dQJoZduy11sf',
    '1dCxibuukfYrbGdXBOqQzOaDB1UTWBG5_',
    '1ZQ1_hX6XmhnTlDKIib8CIfwj4GSrlgLe',
    '1ngE9naHudBZ_q1CzDTIM_jRhP0WtM5DY',
    '1XevsX1UzAXGqDggOOAiYX22xZIr3Pq7r',
    '1zc9Mvpc00nrzW2iHFg6DnC-OL8YuSt_M',
    '1HLbu19KE0AXQgQFxNjn8-OFVSLIGKEzK',
    '1MgwT8eEfeq6paQWS-KBX4sh4Kxlr1T0u',
    '1GfAegER9gRKaMCNmoTnHhx2u33Fo5St2',
    '145ETj3GcrtmwODx4kXBEvTUoljMdkme9',
    '1-msuaQQ5avbXtrMaXnH7vbTdehXkmn1_',
    '1CisV7eWaonayyKjGqKgGdLDgjrB7vfcK',
    '1qhY0hDzGu7CMGhx9Z6efdGPIIGt5OTHM',
    '1YjTXXRl3j7loUpAHEZUoYazH0oGYMKme',
    '1i61g7AJk8iK9FnrWv9EP3fc4iPVsygDh',
    '1gumYiIItunLjLz5tgqFDTjPJXspJlPSP',
    '1XVtaQd5dtSC6g1603s64fFxc-ul6rtzA',
    '15hWkFOpWaV80gJAei8kQc0qk-oRNWG6L',
    '1NOGkU37DcicP8TRFNWE-ol_flThYa5MA',
    '1I3s3bSjh4GShwjtlf2eFw9hKOwXZrpWP',
    '1Aqej8x5-UJN5zQq3k0ACcdbpI4s8fqe1',
    '1FZrM12WFhyHrw3UqfwhrRk7XtITTFZjn',
    '1N6aBE6F-7LenBj7WqHA_Kdj4PAWQCqRg',
    '1YTbjJ9odsG-iHKuQZC8_Bb3qr6de10o0',
    '1NXVABAk4l5bnOL1hWm1rrKiKoZxVj0wE',
    '1kWazM3XrNXWvzPbs81_Ocaan4sJ7vzHI',
    '1nJo5czDFHWFw5HF7PiuQKl9H404jrlhD',
    '1q3D7IM_tBQtu4kDJUN-wPTDmcktP9HlS',
    '1HSrKIsP1KhIxhQByK1xQy3IyKrw0vssE',
    '17WnEDOOhC5jO68w3qc_diAee1M-0IN8q',
    '15jQ96ubN3iQPvzCQLXJnBH7xcFp54IA8',
    '1-aNPBTHbEocranwcSPQu5cddkXwHjlAb',
    '111ozHKWVatsW2wlsMQo7IjK24K-Z6Tet',
    '1RaX71-92LNIdROFAwiohCo5TKc0A0g9Q',
    '1yPIIEjK4bOcXnd81jNIJ_YUHO_cUIwts',
    '1VJSGyAE7QnCIHD6eZs3mzS1lu5GybX-O',
    '1pYkjHb9qhcTXUfWFfxLKqVgzqm0bedBv',
    '1-io1s3Dog3R_vAaier1XrxSeOgqiIn2L',
    '1ZMzgnD2tSsJ0460jyJVyRPjkXas7MNw3',
    '1PF79J88HBZx4NCcPXHx1sPX4P9kC2bzp',
    '1OEg1lI-wykYJoSkWjU5tOOti1QCPJ6Ec',
    '1Wycsj_gnPVwSWWQ6gNE5wufISzWTHQMh',
    '1OX1lUFdLdLN7yyZJR6cnwrXt2s1-pAOz',
    '1kQo0DYBJ6yTMjjezwoH4XKS_OEwDKuMD',
    '1tH80NeV40pb0wF0DQJ1Cv7bwJ84ZxxYH',
    '1d1rUczM7jSKqrqJQUvaUoQ-W7rBDVgH2',
    '1-PbA53TwSYtrgRDKMwkY2L_Slo9WInKg',
    '16o9KnYmT9UBoWvCZ7-6uY2pdFKx483p7',
    '1u3tC5pv1W8gU2O3t08yGM9QEvICkEUIL',
    '1ItbVFaQDTm8UVAQANTKjb1ohVhJtWRf-',
    '1SXdcA8boanYOGYYFpm8yltvffNaQQCfq',
    '1APMobxjXv3v43_yeLkAW0V9eaJTXnaSX',
    '1HlIk8NApGtnXSyjnCSNOesWq_VDm6K1G',
    '1g5vOuhzN8dnV6_fRyKzd2KJdu2AhD9ca',
    '1DlcYUABsW-fhuUZRzd1uZ8GeLJERDL4a',
    '15A1cYbSpH41PJbSikFSDyL6052oLMRNv',
    '1CLVuKMK0ONcaMBX6lIvKBKWtOWyw99Oi',
    '1gm_IVVo-3OM8QHfs7Nv-Z-FtXjee-u8i',
    '1tSyJD1JrxJ1L2k7FWBM74nmoSejiaKyJ',
    '1ZzK1DujXM00OhXaJJddqJFUU17uf8TKd',
    '1_SfQNsgbZHNJwVZ-_lIh7CnHVl8Sewki',
    '1VOQ7k9wLbiRw4sVX6QRq280rqV81YfGZ',
    '1fYsAwYQnTSvzVqjxh3NckLVkZMMZLHpf',
    '1-QKDtoITiz6fBw-4kn1B8HI_O_5eOieW',
    '1-FtXegmkZ8zmJZ6CFVKYxV6Ni-ZkFYsR',
    '1baNfYSejNv_4DthPgFYNTSDw0dnUcdwg',
    '11DZwR5h3TjoNBAjBMWdXshmP-MFrj0BJ',
    '1wruSL9v5mcl_1PlA6YnYGrI10Lhg3XEb',
    '1uyyxbOYxJ-jxKIOfEaLp6klUmVyAAI6M',
    '1isNK6AFvnEfXWmnTEr0s0NJzqvmN8mkg',
    '1akO3hoXAdg9axMMUvcFKB_0qq2vGBd6G',
    '1zoXqB1cJBD9M841Zo5bOG92vCtUXaaCn',
    '1CPyBEQVUtpGFChMi0cLGP1NUgcJjymlZ',
    '1C3FdDOFqUj5K8stoiIZvwwM3eL5gT29A',
    '1daMFJ_DEm5HQX9O0kvcGnH0oqkNyesEl',
    '1x9vxyP6ZnVqJ5KXJOrySwEccwD9dThQV',
    '18hpzbqhT633G5yUbZbPd65WCONkq7XHt',
    '1pVHTkrzOarKUQNGh9u5cJOoTBqTpZfck',
    '1mAHxa_Kn9wskYY5Ue7ad2yiyzCiEL2S4',
    '14kth6oDCC6U22Vh7XIzmAYwY4jiXdpt_',
    '1SKpBKrgDIRiKyHasnBSzVb1oai2tpIUR',
    '1SAVWeH_d2qhuOcq29q_FqBn9elXR_ESH',
    '1SEYKKw2lBafYVe84IrIaGeL6s194YRhr',
    '1OIx87-nEj8kQaLLw0Y0P7k5lUEeiOQ6h',
    '1ET-8D82TrOgC9HEnUvY8sRD33DzrJ-XF',
    '1Njjeac3eMEA60ABp758PH6PfJGD-m_8A',
    '16Hip6wkfm_mLx9T2idPLlKefpZSg84cd',
    '11wCraObcRQFApcmoinP5ehIf1NL1KoBR',
    '1Ljydt5JM-Plf22c3VnKYORb6wgfVVzHB',
    '1ogdxBD5pX4-WqpDvL_TRcGFNYjL3XT22',
    '1A3yhV4Cl-QzBpyt3auiW3_WIoz90CBTF',
    '1uC-Ion0BRmXYDxStdSfA6DAe-2bECJXU',
    '1ozorSanpD060lVxoyrC5uS6ZKY-b4qtv',
    '15Udaaz3VOqsyrh-op-DnHRl0LzjX8Zq1',
    '1zRpxuNr1B9dAZKdmP7RMS1a86vN5Z4bU',
    '1boa6b96KXEMC__W3ghIcHd0XkMaUAr77',
    '17rPDgZ3jkJkAEPKqb8lhwxYoz4JvdIvY',
    '1D572c9a6YRymSr4r11Uq7gKE7rKPFReX',
    '1utTmwyO3dSmNJb3ZonH7pk_0CVikQLjY',
    '1Zk5TTVeklPzXE7QTDgvdKJwpnfPOyzm2',
    '1JK8FwtvajLUIFBPwIEW24lgA2N_gxkVU',
    '1p21iYZvsbKtxgoAuimfkGLDFBYRXHQys',
    '13AOmlwE5aqaOELUj8mLQf8HDNpzucPrk',
    '1ezSwj_GHqS9Yt_DdZYWUVgQSkAtd2Wbl'
]

def move_folders():
    """Move folders to Daily Run RFPs folder"""
    
    try:
        # Initialize Google Drive service
        credentials = service_account.Credentials.from_service_account_file(
            Config.GOOGLE_SHEETS_CREDS_PATH,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        
        target_folder_id = Config.DAILY_RFPS_FOLDER_ID
        logger.info(f"Target folder: Daily Run RFPs ({target_folder_id})")
        logger.info(f"Total folders to move: {len(folder_ids)}")
        
        success_count = 0
        error_count = 0
        
        for i, folder_id in enumerate(folder_ids, 1):
            try:
                # Get current folder info
                folder = service.files().get(
                    fileId=folder_id,
                    fields='name, parents',
                    supportsAllDrives=True
                ).execute()
                
                folder_name = folder.get('name', 'Unknown')
                current_parents = folder.get('parents', [])
                
                # Skip if already in target folder
                if target_folder_id in current_parents:
                    logger.info(f"[{i}/{len(folder_ids)}] '{folder_name}' already in target folder, skipping")
                    continue
                
                # Move the folder
                previous_parents = ','.join(current_parents) if current_parents else None
                
                service.files().update(
                    fileId=folder_id,
                    addParents=target_folder_id,
                    removeParents=previous_parents,
                    supportsAllDrives=True,
                    fields='id, parents'
                ).execute()
                
                logger.info(f"[{i}/{len(folder_ids)}] ✓ Moved '{folder_name}' to Daily Run RFPs")
                success_count += 1
                
            except Exception as e:
                logger.error(f"[{i}/{len(folder_ids)}] ✗ Failed to move folder {folder_id}: {str(e)}")
                error_count += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Migration complete!")
        logger.info(f"✓ Successfully moved: {success_count} folders")
        if error_count > 0:
            logger.info(f"✗ Failed: {error_count} folders")
        logger.info(f"{'='*60}\n")
        
        return success_count, error_count
        
    except Exception as e:
        logger.error(f"Failed to initialize Drive service: {str(e)}")
        return 0, len(folder_ids)

if __name__ == "__main__":
    logger.info("Starting folder migration to Daily Run RFPs folder...")
    logger.info("Note: Mercury folder is excluded from migration")
    
    success, errors = move_folders()
    
    if errors == 0:
        logger.info("All folders moved successfully!")
        sys.exit(0)
    else:
        logger.warning(f"Migration completed with {errors} errors")
        sys.exit(1)