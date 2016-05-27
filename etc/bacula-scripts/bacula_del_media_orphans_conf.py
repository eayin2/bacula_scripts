# bacula-del-media-orphans.py
#                                                                      
#                                                                                                                                                                                              
# Description:
#                                                                                                                                            
# Deletes all associated catalog entries of those media entries, which backup volume doesn't exist anymore.
#                                                                                                                                            
# Set dry_run = True to print orphanned entries without deleting them, else set dry_run=False.
#                                                                                                                                            
dry_run = False
#dry_run = True
del_orphan_log = "/var/log/bareos/deleted_orphans.log"
verbose = True
#verbose = False  
