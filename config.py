import os 
 
class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET',  'dev-secret-20250227')  # 生产环境务必修改 
    LDAP_URI = 'ldap://127.0.0.1:389'  # 替换为实际NAS内网IP 
    LDAP_ADMIN_DN = 'cn=admin,dc=debug'
    LDAP_ADMIN_PW = '123456'        # 替换为实际管理员密码 
    LDAP_BASE_DN = 'ou=users,dc=debug'
    LDAP_USER_OBJECT_CLASS = ['inetOrgPerson', 'organizationalPerson', 'person', 'top']