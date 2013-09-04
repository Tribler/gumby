'''
Created on Jul 12, 2013

@author: corpaul
'''

import sqlite3
from gumby.settings import loadConfig
import os


class InitDatabase(object):
    '''
    classdocs
    '''

    def __init__(self, config):
        '''
        Constructor
        '''
        print "Initializing database.. %s" % config['spectraperf_db_path']
        self._config = config
        self._conn = getDatabaseConn(config, True)
        with self._conn:
            self.createTables()

    def createTables(self):
        cur = self._conn.cursor()

        # TODO: add keys
        cur.execute("DROP TABLE IF EXISTS profile")
        cur.execute("DROP TABLE IF EXISTS range")
        cur.execute("DROP TABLE IF EXISTS stacktrace")
        cur.execute("DROP TABLE IF EXISTS type")
        cur.execute("DROP TABLE IF EXISTS monitored_value")
        cur.execute("DROP TABLE IF EXISTS run")
        cur.execute("DROP TABLE IF EXISTS metric_type")
        cur.execute("DROP TABLE IF EXISTS metric_value")
        cur.execute("DROP TABLE IF EXISTS activity_matrix")
        cur.execute("DROP TABLE IF EXISTS activity_metric")

        createProfile = "CREATE TABLE profile ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            revision TEXT NOT NULL, \
                            testcase TEXT NOT NULL);"
        cur.execute(createProfile)

        unqProfile = "CREATE UNIQUE INDEX IF NOT EXISTS profile_unq \
                            ON profile (revision, testcase)"
        cur.execute(unqProfile)

        createRange = "CREATE TABLE range ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            stacktrace_id INTEGER NOT NULL, \
                            min_value INTEGER NOT NULL, \
                            max_value INTEGER NOT NULL, \
                            profile_id INTEGER NOT NULL, \
                            type_id INTEGER NOT NULL);"
        cur.execute(createRange)

        unqRange = "CREATE UNIQUE INDEX IF NOT EXISTS range_unq \
                            ON range (profile_id, stacktrace_id, type_id)"
        cur.execute(unqRange)

        createStacktrace = "CREATE TABLE stacktrace ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            stacktrace TEXT NOT NULL);"
        cur.execute(createStacktrace)

        unqStacktrace = "CREATE UNIQUE INDEX IF NOT EXISTS stacktrace_unq \
                            ON stacktrace (stacktrace)"
        cur.execute(unqStacktrace)

        createStacktrace = "CREATE TABLE type ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            type TEXT NOT NULL);"
        cur.execute(createStacktrace)
        cur.execute("INSERT INTO type (type) VALUES ('BytesWritten')")

        unqType = "CREATE UNIQUE INDEX IF NOT EXISTS type_unq ON type (type)"
        cur.execute(unqType)

        createRun = "CREATE TABLE run ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            revision TEXT NOT NULL, \
                            testcase TEXT NOT NULL, \
                            exit_code INTEGER, \
                            total_bytes INTEGER, \
                            total_actions INTEGER, \
                            is_test_run INTEGER NOT NULL);"
        cur.execute(createRun)

        createMonitoredValue = "CREATE TABLE monitored_value ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            stacktrace_id INTEGER NOT NULL, \
                            value INTEGER NOT NULL, \
                            run_id INTEGER NOT NULL, \
                            type_id INTEGER NOT NULL, \
                            avg_value INTEGER NOT NULL);"
        cur.execute(createMonitoredValue)

        unqMonitoredValue = "CREATE UNIQUE INDEX IF NOT EXISTS \
                            monitored_value_unq \
                            ON monitored_value \
                            (stacktrace_id, run_id, type_id)"
        cur.execute(unqMonitoredValue)

        createMetricType = "CREATE TABLE metric_type ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            metric_type TEXT NOT NULL, \
                            type_id INTEGER NOT NULL);"
        cur.execute(createMetricType)
        cur.execute("INSERT INTO metric_type (metric_type, type_id) VALUES ('Similarity', 1)")

        unqMetricType = "CREATE UNIQUE INDEX IF NOT EXISTS metric_type_unq ON metric_type (metric_type, type_id)"
        cur.execute(unqMetricType)

        createMetricValue = "CREATE TABLE metric_value ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            run_id INTEGER NOT NULL, \
                            metric_type_id INTEGER NOT NULL, \
                            value REAL NOT NULL, \
                            profile_id INTEGER NOT NULL);"
        cur.execute(createMetricValue)
        unqMetricValue = "CREATE UNIQUE INDEX IF NOT EXISTS \
                            metric_value_unq \
                            ON metric_value \
                            (metric_type_id, run_id, profile_id)"
        cur.execute(unqMetricValue)

        createActivityMatrix = "CREATE TABLE activity_matrix ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            revision TEXT NOT NULL, \
                            testcase TEXT NOT NULL, \
                            checked_profile INTEGER NOT NULL, \
                            runs INTEGER NOT NULL, \
                            type_id INTEGER NOT NULL);"
        cur.execute(createActivityMatrix)

        createActivityMetric = "CREATE TABLE activity_metric ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            matrix_id INTEGER NOT NULL, \
                            value INTEGER NOT NULL, \
                            stacktrace_id INTEGER NOT NULL, \
                            runs INTEGER NOT NULL, \
                            bytes_off INTEGER NOT NULL, \
                            range_diff INTEGER NOT NULL, \
                            type_id INTEGER NOT NULL, \
                            calls INTEGER);"
        cur.execute(createActivityMetric)

        createGitLog = "CREATE TABLE git_log ( \
                            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, \
                            revision TEXT NOT NULL);"
        cur.execute(createGitLog)
        queries = []
        queries.append("insert into git_log (revision) values ('30a9b8bfcb8bb0a8f65ba0053878c73ba05c6705');")
        queries.append("insert into git_log (revision) values ('0545cafc9dbd606fb3d28220a07b2650f7d44ae7');")
        queries.append("insert into git_log (revision) values ('2704a74bc4ad5b949c9f53242eb88f807633642b');")
        queries.append("insert into git_log (revision) values ('994256cd1c064c96f91cc2297df4ec012bd97117');")
        queries.append("insert into git_log (revision) values ('2a56ce28c6b285d4d49f02804068ef1204121957');")
        queries.append("insert into git_log (revision) values ('db5159b865def7bfd02e02bf04a2e3ae1004ff63');")
        queries.append("insert into git_log (revision) values ('9cb66f534d31e3f55b0a586ecebe816ca0a6383b');")
        queries.append("insert into git_log (revision) values ('80d3f4acbd8d3cd323b7e1001807c32e43d61deb');")
        queries.append("insert into git_log (revision) values ('d306fd967bb8277dc0927a401d6ac742785d6457');")
        queries.append("insert into git_log (revision) values ('c8e785cd0b44a3ae1359f2adf483813eb4513860');")
        queries.append("insert into git_log (revision) values ('4dffa7e94ec43d1a2e8e794cad7241a9f02e7acf');")
        queries.append("insert into git_log (revision) values ('4315f59b721dd9e447d622b94b2a5f9607e429ae');")
        queries.append("insert into git_log (revision) values ('3084bae0a6c6b32c97b68f454986bd91d8d5d2f7');")
        queries.append("insert into git_log (revision) values ('7cdab65575dc76646cef3fa1faaa2675491bbf8f');")
        queries.append("insert into git_log (revision) values ('98922c95960283164efeb81e65bbb52eed220428');")
        queries.append("insert into git_log (revision) values ('683c6af33ef9a9ac4a6d4590683d755e852859e5');")
        queries.append("insert into git_log (revision) values ('08fa98ab7cd76051a24ec017c6fc4c9ef21fbded');")
        queries.append("insert into git_log (revision) values ('7b84e489b37246f7531170e5bbfd1757302e164b');")
        queries.append("insert into git_log (revision) values ('91820dbc83a3eb0ed0cefc8e602c3bc3de3cee3a');")
        queries.append("insert into git_log (revision) values ('d645146631a6788fe131d9aa9fa024aa8599dd11');")
        queries.append("insert into git_log (revision) values ('1ea031f7d665518721c24635e857d2ffef1c2d9f');")
        queries.append("insert into git_log (revision) values ('0e46536e85ac142dd139d0f42f85667614f48afa');")
        queries.append("insert into git_log (revision) values ('03dfe2e5bbdd9a5cb6a34f48dc584e6f4ddb8ec6');")
        queries.append("insert into git_log (revision) values ('b02bb5ea42ce540a3135f9de8a058f19327025ab');")
        queries.append("insert into git_log (revision) values ('15532fcdb26c611be6370ebfdd5ce039e859774a');")
        queries.append("insert into git_log (revision) values ('a54a992869ac249c259497daf0d26a9db0fd0030');")
        queries.append("insert into git_log (revision) values ('33b6b738ef1d35b7dcd9c59e5cf7fbf1c25cf20c');")
        queries.append("insert into git_log (revision) values ('41171626a0c8f11b79c470aaa91b3a9a757487a4');")
        queries.append("insert into git_log (revision) values ('4200adf9300f9df109cf1a9454419da4b748b323');")
        queries.append("insert into git_log (revision) values ('dea5aef1fee9e488869d09f25b694aa97523759e');")
        queries.append("insert into git_log (revision) values ('01ce8fcf436149293d457eb25cc3b24149dce93e');")
        queries.append("insert into git_log (revision) values ('3e27940e32017c6cd524ca4b61e1e7d4f779c4b6');")
        queries.append("insert into git_log (revision) values ('615d67f2f4b3645e686109bc4c09d30e9e3f1c69');")
        queries.append("insert into git_log (revision) values ('399af0c5af82334d6c60cdc15e98dcbd89db27ee');")
        queries.append("insert into git_log (revision) values ('466caab5b908c70529b21f252d10729996ee7d67');")
        queries.append("insert into git_log (revision) values ('fa67db808d1601e3943f71db10dab8787f195b2b');")
        queries.append("insert into git_log (revision) values ('c68aceb701daa240f6a46526a4f1ef3904a0b095');")
        queries.append("insert into git_log (revision) values ('67382d28b57d027c6efece957a2448b6feb7e68a');")
        queries.append("insert into git_log (revision) values ('d398c5aecb5f4859f142b94f961f56b3776bbdba');")
        queries.append("insert into git_log (revision) values ('c7527c8892c820181d1ba9fa77abdae4ef1f1e59');")
        queries.append("insert into git_log (revision) values ('4bd7ca42991b6f1099a715eb52006110de745a80');")
        queries.append("insert into git_log (revision) values ('4b9a07ff61a9160ed143ebd1bc3c219cb2015052');")
        queries.append("insert into git_log (revision) values ('5234325e6d30d592faf6f7419319fe6a5b791d14');")
        queries.append("insert into git_log (revision) values ('f72c083e7c91a4bcbd1be88dd670be8da72e57ac');")
        queries.append("insert into git_log (revision) values ('64d381431fa6757a70bb71f36d90686e8ce30e63');")
        queries.append("insert into git_log (revision) values ('c8da9d2a25b06934cf26d19c4bace6ec06ad66ca');")
        queries.append("insert into git_log (revision) values ('9423ce47e3e289a777114e402395493feb73c165');")
        queries.append("insert into git_log (revision) values ('c1e289fd47aa0c222e363d98c517373a84378dc1');")
        queries.append("insert into git_log (revision) values ('d13529bd306bb7eaa16f1499232894c29c7ff2e0');")
        queries.append("insert into git_log (revision) values ('ec8d811ba55c5c9f62e106d102364e9126a02047');")
        queries.append("insert into git_log (revision) values ('8f13c27c541e6de4c9848af3514ac04c51002bc0');")
        queries.append("insert into git_log (revision) values ('b700d4c12909d42ee40c00dbc8d147b57e76bbae');")
        queries.append("insert into git_log (revision) values ('6d3f860944b8e3646121dac49d59ec20f7b0adcf');")
        queries.append("insert into git_log (revision) values ('433656841f1bf7255c1964bd8501be2944ed3d70');")
        queries.append("insert into git_log (revision) values ('8272e36f8eccf3dccf5a647c54b922974455e8b0');")
        queries.append("insert into git_log (revision) values ('c11ae606e1030c870f6464ce88bb2b5ba3af4be7');")
        queries.append("insert into git_log (revision) values ('db10a536bbf381eed9297470719eb6ba852f84ad');")
        queries.append("insert into git_log (revision) values ('eda1dff391746446234f1cb86693e327f3472ffd');")
        queries.append("insert into git_log (revision) values ('5a3eafa81238134acf7f04d1db4c1b6895f07111');")
        queries.append("insert into git_log (revision) values ('d3b397eb037a984c5b63d948df30ce9e57282808');")
        queries.append("insert into git_log (revision) values ('0f25326ae11b78deaf6bcd946d8761975d7ccdcd');")
        queries.append("insert into git_log (revision) values ('e34e0bc34b6e740bfab1f10fdf9be29d5bf20aca');")
        queries.append("insert into git_log (revision) values ('29f231d420eb030f05e1d996903869c3a7a9be74');")
        queries.append("insert into git_log (revision) values ('c36c1f1345cfdeb3f1e2d88b0eba75ca2e398af3');")
        queries.append("insert into git_log (revision) values ('6916328dace43a7b04589fa493d4772626beafa6');")
        queries.append("insert into git_log (revision) values ('c9e829192ba83dd9dcf3abf6bf10b45b27efe0f7');")
        queries.append("insert into git_log (revision) values ('d06c96cb7d82ea1c8b64907a4cae780df6997fca');")
        queries.append("insert into git_log (revision) values ('f5129e811b234e682b5db62ac6e8a7e2426ff265');")
        queries.append("insert into git_log (revision) values ('038f3ae2a9ee7271c1fb6b3497d24bf94b12a1f5');")
        queries.append("insert into git_log (revision) values ('7370da173517da83db91db0532e5c7e57c61aa90');")
        queries.append("insert into git_log (revision) values ('30ceef7ffb49d1220199d9e6e4195ee9917698d4');")
        queries.append("insert into git_log (revision) values ('2cdaaba73021475d4916e32848a2f1acca0f57fd');")
        queries.append("insert into git_log (revision) values ('243603fc16e912d15b8757b394f1c0559336e705');")
        queries.append("insert into git_log (revision) values ('81bc681710b5fae1ef75a6e83a4b9085b91e1279');")
        queries.append("insert into git_log (revision) values ('869e9d324456fe4c91aa622c5a2aa9cc488b6042');")
        queries.append("insert into git_log (revision) values ('182f1e0891facfdd7e4f29fd429fda6a4b769e9e');")
        queries.append("insert into git_log (revision) values ('c8562d91da853ab732f7ce8f5f810c6ad1cd1ccc');")
        queries.append("insert into git_log (revision) values ('8077681327388ffbf9523fc69488a5c15a0efb22');")
        queries.append("insert into git_log (revision) values ('5eaddcccdfcf7c10989e646a462d3bdb5a70ea67');")
        queries.append("insert into git_log (revision) values ('b180c4676ce236492eff704b28b04f39716864fb');")
        queries.append("insert into git_log (revision) values ('d6a395d38f2668046cbdd2380c5264372e84b1ec');")
        queries.append("insert into git_log (revision) values ('d815ec49f78b0182a306f21156464c93bfaa4343');")
        queries.append("insert into git_log (revision) values ('49b84acbcb8fe7ed5f5bfdf550e1403e3b6e3a88');")
        queries.append("insert into git_log (revision) values ('aeb8033e13f756f0f7c0afbd009b85ab6f36bb4e');")
        queries.append("insert into git_log (revision) values ('8c864f8cc575fd6dddd39de33c55820e54754344');")
        queries.append("insert into git_log (revision) values ('892d5605bf370d98c492f42a64d34558837efb91');")
        queries.append("insert into git_log (revision) values ('e7110e772343843b6f3ce246591cf8ee27c9d714');")
        queries.append("insert into git_log (revision) values ('2eaf82275385a26dfde4ea1a43c8ecab14ef74e8');")
        queries.append("insert into git_log (revision) values ('487731c292fcea22d5107a587bed8e4779e033ee');")
        queries.append("insert into git_log (revision) values ('d821c2face63cacc091222b6a16581e8b90b6130');")
        queries.append("insert into git_log (revision) values ('22a29250f31efae8d5507c9d97586872eb8100c9');")
        queries.append("insert into git_log (revision) values ('0558bc4680adb24cb0d67a9321ca3ad75ac903fc');")
        queries.append("insert into git_log (revision) values ('0a74acefbbcebcdfd04fa5c6cad507285f5de43a');")
        queries.append("insert into git_log (revision) values ('6746412917164609b2bb3030f8504ebc9bacb2be');")
        queries.append("insert into git_log (revision) values ('d958465607bb5b038c0ef7fa2eaa4fb0885427f6');")
        queries.append("insert into git_log (revision) values ('03fa89cce2a161897a32fe658886f520cc0bd96a');")
        queries.append("insert into git_log (revision) values ('367efd8daaaaabef915fabb6cd8e77404612216f');")
        queries.append("insert into git_log (revision) values ('24ee9859e92f203799ea84f2a6f9feaede3442f1');")
        queries.append("insert into git_log (revision) values ('e636342691d601e749edacc5e9b76260ee732bef');")
        queries.append("insert into git_log (revision) values ('141a688a653f1015b54886e115bfbb202852e8e7');")
        queries.append("insert into git_log (revision) values ('8067c871c05943827ca3c359b0c12f0f2226566b');")
        queries.append("insert into git_log (revision) values ('5f51c66b19c029fe17ed5a4bc4e92d9073515a53');")
        queries.append("insert into git_log (revision) values ('255d50417d7121745ac54c38f5b6d3b1b59b17e0');")
        queries.append("insert into git_log (revision) values ('89e98d02c83c41cc6a1eec5e76176e353acca2d6');")
        queries.append("insert into git_log (revision) values ('21974f1bd1608d31c2d8a635f02ffbadaabd5b6d');")
        queries.append("insert into git_log (revision) values ('b8eab4fb501213ae151372cd83a6131582e2ad6b');")
        queries.append("insert into git_log (revision) values ('6474e0700a0050c82475e26ff688f45114144810');")
        queries.append("insert into git_log (revision) values ('8730442bbbc9471529e00e5dfe84ef300038423c');")
        queries.append("insert into git_log (revision) values ('c6f9615c24f45f52e6252c05cbf29797f263e60f');")
        queries.append("insert into git_log (revision) values ('7154b95f8247854bae553531a0e2a43c59a2cc1e');")
        queries.append("insert into git_log (revision) values ('535c7d0cdce3e65e6c03306e36a877f5505e9cdf');")
        queries.append("insert into git_log (revision) values ('5252eefca8c655270e997a8f76888a4e91ca2637');")
        queries.append("insert into git_log (revision) values ('d7a84eb4268cd6649e96283d2806882bdf7908dc');")
        queries.append("insert into git_log (revision) values ('f5d2ffc9ff70baa267a7dedce02a164d236aff68');")
        queries.append("insert into git_log (revision) values ('4067ab93928f931d1c3b3d74b970433288b9db67');")
        queries.append("insert into git_log (revision) values ('3967b71ce54aa1f9c9faa2840f241024c787ad4b');")
        queries.append("insert into git_log (revision) values ('88f622802eac79c07f76305eb202f9561b955354');")
        queries.append("insert into git_log (revision) values ('cafe6d11b43dba4fd0de846c875ddefaced9e904');")
        queries.append("insert into git_log (revision) values ('c232fc8a57bf555edad74aa0e3526ba8a13c75b9');")
        queries.append("insert into git_log (revision) values ('09e38def4a0561c589756044215a1624f062e98c');")
        queries.append("insert into git_log (revision) values ('77a55f70e9fbb7defa68ec4cd680e05ff2166c81');")
        queries.append("insert into git_log (revision) values ('44663aec7cd119e63d8feedaaa871cd9a5074a9d');")
        queries.append("insert into git_log (revision) values ('15cf8e4fff0125b01cdb60991893beaf0566bc47');")
        queries.append("insert into git_log (revision) values ('e303dee7a8075a773340563e731a70d4b3206752');")
        queries.append("insert into git_log (revision) values ('32e0ac86cdc537a9d792b2374e670cbbbd147cbb');")
        queries.append("insert into git_log (revision) values ('03dfac7fc3a2a3d5ce76cd407ea97a97c7635215');")
        queries.append("insert into git_log (revision) values ('a8ce55f078e54b7c43b849616f0a8fae06ad69f2');")
        queries.append("insert into git_log (revision) values ('4650b9c9cbd971a6fff4e16c6e59747f025f3b6a');")
        queries.append("insert into git_log (revision) values ('b92578988d0c0d52e1f71006f43d0dada5957760');")
        queries.append("insert into git_log (revision) values ('615f003801a85886da20e7422b6ac84b27e6269b');")
        queries.append("insert into git_log (revision) values ('7db88189d2e2d51dcae9e062daf22145723df041');")
        queries.append("insert into git_log (revision) values ('b2a9d5387de3e39375bf88dc0b60f0fb55771cb2');")
        queries.append("insert into git_log (revision) values ('bcb2e3de98fc1547b88989472a3c5996a61f37d4');")
        queries.append("insert into git_log (revision) values ('89bc99b72e602017dddc37d04af43e820c8f3b43');")
        queries.append("insert into git_log (revision) values ('9337a1449699ac0a5ff6e4ecddefc0256a9007e7');")
        queries.append("insert into git_log (revision) values ('2b842c0422249e40b5abe23e9712339d1ca98d62');")
        queries.append("insert into git_log (revision) values ('51907cceda71462ae574dfd75d753009b4ff26e8');")
        queries.append("insert into git_log (revision) values ('3b03150f9161f54f680483116b95deb2faa9d83c');")
        queries.append("insert into git_log (revision) values ('4b08c8274e19004ae0e124e309dc23b2884a68ac');")
        queries.append("insert into git_log (revision) values ('02052dacfb3267645b9305a6635f0cb2ad97d64e');")
        queries.append("insert into git_log (revision) values ('16f8d5a5f5a0d209c4bec25b1e95d0604722e05b');")
        queries.append("insert into git_log (revision) values ('2f42ec2abf84c95a115de2c9d0ad995a80f0386c');")
        queries.append("insert into git_log (revision) values ('3b698354e1ce7574811e97c48841ca2590391428');")
        queries.append("insert into git_log (revision) values ('849b4c855ebc6ad344879126490ffb1e1edfbef2');")
        queries.append("insert into git_log (revision) values ('fdac0562b33faf3292f863954249311faebbd5dc');")
        queries.append("insert into git_log (revision) values ('3aec130c6f36f9dd655ff0770d3ce592ab8329ed');")
        queries.append("insert into git_log (revision) values ('67af9c7df9629b2760c947661a287f6191b60b0f');")
        queries.append("insert into git_log (revision) values ('462e9155a47b3cb02848c9cd7c3cc0c9ef44002f');")
        queries.append("insert into git_log (revision) values ('fb8c71c5e88addcfa2e8396e89c403ea962f65cf');")
        queries.append("insert into git_log (revision) values ('6e13bcf3e3767e1fa06cd17572ef8c516302bf0e');")
        queries.append("insert into git_log (revision) values ('6f98082c3c47d09d713afa1ecef0e8b96e73c224');")
        queries.append("insert into git_log (revision) values ('8fd21ec3c03bf833155b29216fd459d8e9e06a1d');")
        queries.append("insert into git_log (revision) values ('448816e69f8361567c9246c5361ca8701e0a5988');")
        queries.append("insert into git_log (revision) values ('6ca86b350d6efc83bb2bffc8b5b7cb1c873bbe8a');")
        queries.append("insert into git_log (revision) values ('b607816085b374cfbf8bcc804da78beaf527ee29');")
        queries.append("insert into git_log (revision) values ('c89e07c896ab2eaa70fdb98bea4b19416e3efa09');")
        queries.append("insert into git_log (revision) values ('a6e6bd2d57211cdc2a39d47bd596b355e7bf941e');")
        queries.append("insert into git_log (revision) values ('c1f31c74031e2c803be5bc01b6b3e219863156e0');")
        queries.append("insert into git_log (revision) values ('402c90488be9bfddff178476c80351e4722ea592');")
        queries.append("insert into git_log (revision) values ('ab8c38bfe7d96a118959e438bd2d2695cb8a7d9c');")
        queries.append("insert into git_log (revision) values ('6149a9b131575a6b063e7a8a05895ed762707c8a');")
        queries.append("insert into git_log (revision) values ('0db890af47468d2cd84aebaccbad600d3b9c01db');")
        queries.append("insert into git_log (revision) values ('6c6ddf4f8819a0059d0b379805a893e76713b6e9');")
        queries.append("insert into git_log (revision) values ('e031feba880694192730cea68d82a856b8be50d9');")
        queries.append("insert into git_log (revision) values ('be2f21df7419b60a16eb47a82da0e1a9249e22b5');")
        queries.append("insert into git_log (revision) values ('f2fa70de4c96d2e61b0531bc08a080cba070c2b2');")
        queries.append("insert into git_log (revision) values ('30a49c99fca87e6d4831feea844096027a9e9c42');")
        queries.append("insert into git_log (revision) values ('a2f2267f3f697cfbe278830de6262733c8fa98ad');")
        queries.append("insert into git_log (revision) values ('e04ce07244471fb6baa600f7db5db4d941f63973');")
        queries.append("insert into git_log (revision) values ('418dc96a34d871187fd20f8e44c853cafb9d095c');")
        queries.append("insert into git_log (revision) values ('1592aa89aed7286cf4643bcbf07aa4e324044a9e');")
        queries.append("insert into git_log (revision) values ('7fbfa0d29af5c2a10d187662ae7f61e2de6d54a0');")
        queries.append("insert into git_log (revision) values ('e01f4348ca532e57429ef2697555cc1e1482a249');")
        queries.append("insert into git_log (revision) values ('fb2ad1d6b15f93c828810f77bc89b6791b616285');")
        queries.append("insert into git_log (revision) values ('36198166bbac5addd06995b13b508419925e154b');")
        queries.append("insert into git_log (revision) values ('fd3e1bf51c6caa79c34b88e8cf3f94202c80c61a');")
        queries.append("insert into git_log (revision) values ('ed3448db1ad6a1b0fa6f4e66d1c4a2767580b908');")
        queries.append("insert into git_log (revision) values ('6b65d83ce737eecd614e9e03458e8219def8ecd9');")
        queries.append("insert into git_log (revision) values ('602c302c32b4d86ac7b2407cf6a06083b29be0d3');")
        queries.append("insert into git_log (revision) values ('0cdd7c66681ed4facc8179de4ab90028743a6f97');")
        queries.append("insert into git_log (revision) values ('279e8e6499379c0dfc1333de7b1ce475bed067ba');")
        queries.append("insert into git_log (revision) values ('9e66d3e2c76a8f7733dd79d3179b5f44aaab950c');")
        queries.append("insert into git_log (revision) values ('ca2f9d2cea95db4eef8ebb136b4c53c64b9ab94e');")
        queries.append("insert into git_log (revision) values ('8ed12d1ad53222af701f093614064a0fe64a2c6e');")
        queries.append("insert into git_log (revision) values ('5a598f123339e4233eb545f746e348889b87edfa');")
        queries.append("insert into git_log (revision) values ('fec95fbf0e9bdecd7ad3e3827825b3f91f8c3dd8');")
        queries.append("insert into git_log (revision) values ('d7f1cd95c3fec2f5601969253450efce3bb62986');")
        queries.append("insert into git_log (revision) values ('d5074f4080e3f30769a5be5e11dfb306f42e1f6e');")
        queries.append("insert into git_log (revision) values ('3900749a8d592dd95d8e5c1f473dc8476415d4e7');")
        queries.append("insert into git_log (revision) values ('12cdf9bbfe3963a204f165598fc679fa078cbfd3');")
        queries.append("insert into git_log (revision) values ('3a2be79963789bcadbc5d06e1b896ecbe97e9438');")
        queries.append("insert into git_log (revision) values ('f990cc7faea72e09f36c7c1498ed48e655f5a0d1');")
        queries.append("insert into git_log (revision) values ('118762ff3aeec828baaa85396bcd636e5c595e26');")
        queries.append("insert into git_log (revision) values ('1b3485b40f08add4b1dd2c58c735d3ebd3493343');")
        queries.append("insert into git_log (revision) values ('d2af6d4012dcfecdd6d9b4aa72a0a50e4388e319');")
        queries.append("insert into git_log (revision) values ('4b6e094d3a4e095b543876b9c4157a307decd3d9');")
        queries.append("insert into git_log (revision) values ('037766d6065d26dec35c9896575b6e43e31737d0');")
        queries.append("insert into git_log (revision) values ('2a8ef1643ebf6641df0f87a6987434b6e6bc465a');")
        queries.append("insert into git_log (revision) values ('6a0e6d73ace8735b601a3177c90ef210fde6db3b');")
        queries.append("insert into git_log (revision) values ('7552b1e558e5c08e0e869cda8abc3c5ae50a11f5');")
        queries.append("insert into git_log (revision) values ('013f2432b9bd1e4929d017bfd9484a620cb07174');")
        queries.append("insert into git_log (revision) values ('fcb4759a22df981b39386e3c10dc809a88de1d8e');")
        queries.append("insert into git_log (revision) values ('9c93bdc00a5f992b4ee800004bd4b562c847eed8');")
        queries.append("insert into git_log (revision) values ('1d1e5583735e1330aa5103e16f8fb56086b920ce');")
        queries.append("insert into git_log (revision) values ('04ba166fbef7e92fe59df6df01c21f6d33a0902e');")
        queries.append("insert into git_log (revision) values ('d5259151e3ad44ca3b4cf580e17abd777f99ae2e');")
        queries.append("insert into git_log (revision) values ('710f054a9debd433cb88aa06a5d37eba9c15fb37');")
        queries.append("insert into git_log (revision) values ('967aa35011ca3f4c4aff37113c299e5110b2afcd');")
        queries.append("insert into git_log (revision) values ('cdc16187894bf1ee26ae1ca14734e20f07e9e90c');")
        queries.append("insert into git_log (revision) values ('58d1a9a20cd3fe0be88feec9fc6452b7000a6ee0');")
        queries.append("insert into git_log (revision) values ('88a57d13c61be9afadc30f294e301ffc6f466ac0');")
        queries.append("insert into git_log (revision) values ('49f775dba0741d543ba5c7c7406d9ead726873d4');")
        queries.append("insert into git_log (revision) values ('c953a9c704d6945b596747ada5023b731065450c');")
        queries.append("insert into git_log (revision) values ('7320bb6b7abbf68120dec529034d45edd6575bd0');")
        queries.append("insert into git_log (revision) values ('d9657c22cef4b6da0e16ba519479d044b1be9ead');")
        queries.append("insert into git_log (revision) values ('1e892ef91d07f6dba2919b7ff4fab1622f5d1b6f');")
        queries.append("insert into git_log (revision) values ('f71c33c1158f6ef09c1c42cc36751281a1371b08');")
        queries.append("insert into git_log (revision) values ('3676329adfece664a178eeada62afc42db879e7c');")
        queries.append("insert into git_log (revision) values ('e2fce54911a0ffb9f49dbf5f9d557c9764eed0f6');")
        queries.append("insert into git_log (revision) values ('18623d56ac35faa456c2827eb191c3807a262ecc');")
        queries.append("insert into git_log (revision) values ('8a6922299baf8c90d88447efcd3858a11f5c1e70');")
        queries.append("insert into git_log (revision) values ('d1dbf7e25eeac6b829618514a2494368ddf55a79');")
        queries.append("insert into git_log (revision) values ('65c393c8fd4194234d2c0b49ea174d03165f2d56');")
        queries.append("insert into git_log (revision) values ('4e2f9dde4fa0ebb497d075ecbaa36f28d8590fef');")
        queries.append("insert into git_log (revision) values ('e9d57606181d55c0bd3e464562e118425faf5a8f');")
        queries.append("insert into git_log (revision) values ('f0e6943f69b7913066a3aeb808966177638d0a84');")
        queries.append("insert into git_log (revision) values ('64f1c28bcad0bd7376109005ea09a224ab6a0fb4');")
        queries.append("insert into git_log (revision) values ('05f9246b5c92c5300c09045628a4b4b65091ff6c');")
        queries.append("insert into git_log (revision) values ('c615952b005a3901705f5fdc59ddfe8a14f2f755');")
        queries.append("insert into git_log (revision) values ('b112ce544ee7b419eff9dd5f444f15ff77f766c1');")
        queries.append("insert into git_log (revision) values ('c07c459e276237c6e83ff15813937bed08e2e6ca');")
        queries.append("insert into git_log (revision) values ('751fe98d34546b09877bcf4bc42cdc58ec9a63f5');")
        queries.append("insert into git_log (revision) values ('ee7282bab450e42703d4fca33f7001f4c515fcd4');")
        queries.append("insert into git_log (revision) values ('5a1abef8205f6f5ef53661221828b29908298c77');")
        queries.append("insert into git_log (revision) values ('7793f3b38ecdf7a6864a22eac006e436d1f3f450');")
        queries.append("insert into git_log (revision) values ('1ea79874ea739f295365f909c343ec8ec73dde18');")
        queries.append("insert into git_log (revision) values ('54eeb5b6637e817e3d97ba2394bcc2c3d3d86596');")
        queries.append("insert into git_log (revision) values ('c66c5b91f1994fc5f6ff2cfd5b8be4d891d842a9');")
        queries.append("insert into git_log (revision) values ('618823aff9d66a6e6d96b4a1eb554bffc8488914');")
        queries.append("insert into git_log (revision) values ('085186b83022f285d2eafb25da504333602d086f');")
        queries.append("insert into git_log (revision) values ('c7635c9fbc191b151cb972d148c09f0686336375');")
        queries.append("insert into git_log (revision) values ('2a21dcc94049185654e27394b94e6cd0ac553b90');")
        queries.append("insert into git_log (revision) values ('89e934fb294dc7deb32d5f8e7bfb0434a4cc948a');")
        queries.append("insert into git_log (revision) values ('f4f5ca348405c3bb25de3fb1ae97a9a105ceded7');")
        queries.append("insert into git_log (revision) values ('3dd6b9ee9256b5e7217a00dc456f6601813572fa');")
        queries.append("insert into git_log (revision) values ('773ae85701fb5216e8716843a3e62cfe2c656b17');")
        queries.append("insert into git_log (revision) values ('83dd607e42963d6d35323225311f2ed2a2eebeb5');")
        queries.append("insert into git_log (revision) values ('dfd7385ce5750472303eefd762913908fde9e5ff');")
        queries.append("insert into git_log (revision) values ('46c7f865b88741e577935c28318b04e8b753ad85');")
        queries.append("insert into git_log (revision) values ('d56a1bdf33b46c638bba7d5ac6d0481890f63be5');")
        queries.append("insert into git_log (revision) values ('9940e2b5cafc94372b716f5ab43e81f399293ded');")
        queries.append("insert into git_log (revision) values ('487d57e7a70c7f9c572cf4321f4012af1cf54232');")
        queries.append("insert into git_log (revision) values ('e79990417bb3555aa2816a4ed79d8c5c8fdcfe10');")
        queries.append("insert into git_log (revision) values ('28d98b89c25bc382c1ba4360ef9069e84418b63f');")
        queries.append("insert into git_log (revision) values ('8d83f5e5bb647d7d3195b72891f999fa086e2a9e');")
        queries.append("insert into git_log (revision) values ('69d27e4a4fb86fd7ca228e1f92ceffc6845bf6cb');")
        queries.append("insert into git_log (revision) values ('e509cb1da2d3925cb636d2edd897f5f1780023bb');")
        queries.append("insert into git_log (revision) values ('5e381cdf277c14445bed355d6516252581041072');")
        queries.append("insert into git_log (revision) values ('1e41176ba6f2acff9532575283328c3c0284bc60');")
        queries.append("insert into git_log (revision) values ('cff6fc7ace9f4971d36bcd156740b9ea527ddd75');")
        queries.append("insert into git_log (revision) values ('85f8b1545a21fcf815848797cdcc118856705b76');")
        queries.append("insert into git_log (revision) values ('0fdc43b87aebd7d1dd7af81ef8c04893e0086c27');")
        queries.append("insert into git_log (revision) values ('1ec5ad19b5491d69457b796febb5b767efeae433');")
        queries.append("insert into git_log (revision) values ('ae6d3c89e2152002912f788abe3ba522ccf33f84');")
        queries.append("insert into git_log (revision) values ('16ac1c9e6ab86070528a7b0829e7a82217fcbe5e');")
        queries.append("insert into git_log (revision) values ('7e5dc764dbe32f3e636849414d36bc611f01cc87');")
        queries.append("insert into git_log (revision) values ('a27476deaf142fe3dc45ea14abf51a572d0c6d50');")
        queries.append("insert into git_log (revision) values ('2fce9820d8b20cdd55737107a5f57a6b7844600c');")
        queries.append("insert into git_log (revision) values ('abb39c89128dc04e5e0271ea471a8596f021b896');")
        queries.append("insert into git_log (revision) values ('1799a7eb2aa082cab62766c57feba6e094984979');")
        queries.append("insert into git_log (revision) values ('38dc93598f55c9fdcf439ef45d3fd664542f841c');")
        queries.append("insert into git_log (revision) values ('1ec1bb308df9c6d3787e1e067230bd5aeadfaa1c');")
        queries.append("insert into git_log (revision) values ('f0e0b1c26aa4a65daa33a070749ced9cc3ef822d');")
        queries.append("insert into git_log (revision) values ('d4091dc8928e1cbf115a9e67bd8c6c189822b3d4');")
        queries.append("insert into git_log (revision) values ('b5134f7dfa5be5908f793f756dbd13a5233daec4');")
        queries.append("insert into git_log (revision) values ('aeefb2b9a3f950aa8f3570156222e7583ebed747');")
        queries.append("insert into git_log (revision) values ('52545e3e4593491e774e37091d965d5f4c3391c4');")
        queries.append("insert into git_log (revision) values ('1ff4d2d8620ea3d44d2dfbe20a6ddd456550e594');")
        queries.append("insert into git_log (revision) values ('4852925e24d902004ec22ea0ebcc4e52f5c370f6');")
        queries.append("insert into git_log (revision) values ('3ea3a08559d09a30106b4348f6f1c452e9667b9c');")
        queries.append("insert into git_log (revision) values ('a3889f445061e6699ae8ae1aad8be110d0205daf');")
        queries.append("insert into git_log (revision) values ('5a566e85a96de0fd56c8116357a8b74eb5efdd9f');")
        queries.append("insert into git_log (revision) values ('09c822988204c4c90eeb0da54d0125f8aa6c784d');")
        queries.append("insert into git_log (revision) values ('11c85c9b6e3fc710cbfaa70c63a68fd1e7c0ab46');")
        queries.append("insert into git_log (revision) values ('c2ca775ea0c9dab60e492a08f760d76716e9d6c0');")
        queries.append("insert into git_log (revision) values ('d9b55f681660e61a134df1c598b1116c3032bced');")
        queries.append("insert into git_log (revision) values ('9220a413bfeedde1d769cb1ea03c1231594a45a7');")
        queries.append("insert into git_log (revision) values ('ac1b1a9f6698a5f239d7f5f0eb42574c66478cf5');")
        queries.append("insert into git_log (revision) values ('c87f00476ca45516e50221f2794f7c154adab74c');")
        queries.append("insert into git_log (revision) values ('9ede58c247ee96bba27e49eeca262b24fdb07824');")
        queries.append("insert into git_log (revision) values ('f378ce0b1494509075e0d21945ee1cd9a741ded0');")
        queries.append("insert into git_log (revision) values ('0b1d50bac2b79fb4f814b7179ee2a202e8707666');")
        queries.append("insert into git_log (revision) values ('e3626fd8c778235a6af2e5218798648393b91ab3');")
        queries.append("insert into git_log (revision) values ('b19afadf32936cebff17fd8d59bab584f9b2cd06');")
        queries.append("insert into git_log (revision) values ('91d596028f74072388c85fc67680db6294a0395b');")
        queries.append("insert into git_log (revision) values ('f449c8f8721c1ced20bd23232ef010586e3944c6');")
        queries.append("insert into git_log (revision) values ('2cc4edf7ac5f374832546cca360b52959e433b7f');")
        queries.append("insert into git_log (revision) values ('9100ebdb9f9d495af554bf5a9f1249dec6b01c5a');")
        queries.append("insert into git_log (revision) values ('0061a6f122d64b89469d4ac2cfc411e61b15ceaa');")
        queries.append("insert into git_log (revision) values ('44710730512055d081b3e10e66f1ec3d1e0b67c7');")
        queries.append("insert into git_log (revision) values ('621285b0f75955c6e7f757be11cd5b99fe27fbb3');")
        queries.append("insert into git_log (revision) values ('51c8ca20c4f39a5fb76778f719a43db9ec95ecd1');")
        queries.append("insert into git_log (revision) values ('a2888398e0e36fb8cf3f832b92767f61a76fd23d');")
        queries.append("insert into git_log (revision) values ('49bc4e012cd73690e760f65073bf2c44a5927b21');")
        queries.append("insert into git_log (revision) values ('68628c2a5adde7b926c584ff6fafaa32818b7ddd');")
        queries.append("insert into git_log (revision) values ('6fc3314014e753eb887c36c80d90e285af99a26c');")
        queries.append("insert into git_log (revision) values ('2b221fe4d38fc74fe0da36df4f4885abbb27b4a3');")
        queries.append("insert into git_log (revision) values ('05793ef8326956c927615a4f89b244c1c536aa5c');")
        queries.append("insert into git_log (revision) values ('5c502a996455cdff4fefff3ddad06a2fe3dba316');")
        queries.append("insert into git_log (revision) values ('fa764803b7bf5680bd1682455f9962cdd2e90db3');")
        queries.append("insert into git_log (revision) values ('25551e9293340b3056c5bae4d0cff7046415210e');")
        queries.append("insert into git_log (revision) values ('d75017ddaea9bd234260152f3b75d935e58c5120');")
        queries.append("insert into git_log (revision) values ('798c9339f6829f49d53ea2887a8ed38f4adef3cc');")
        queries.append("insert into git_log (revision) values ('5e9e85246afef6992d7928237c08c28db648b528');")
        queries.append("insert into git_log (revision) values ('2398060c03ff7d081fb251cc0e2833a02abbd3ae');")
        queries.append("insert into git_log (revision) values ('e022187ba44a43658b89724f3755c53d74f27c17');")
        queries.append("insert into git_log (revision) values ('63fd384c6eb3ddfc29c1363141ae998bcf7e7620');")
        queries.append("insert into git_log (revision) values ('5ccda3d59df2287f5995a9aa40e453ea2b982711');")
        queries.append("insert into git_log (revision) values ('7f84afd8adc19cde6b8fbd6d00e5d4f1cea26bcf');")
        queries.append("insert into git_log (revision) values ('5282b1483ec44ae6e5d22708192243326f187c13');")
        queries.append("insert into git_log (revision) values ('eddf9f0cf2723e17f3e09772872b3ae601b4be10');")
        queries.append("insert into git_log (revision) values ('c385efc64f090dfffab864cb901c6e8547ffe0a9');")
        queries.append("insert into git_log (revision) values ('4325692fe7865518e8a4690c2ea6efccd10d77a3');")
        queries.append("insert into git_log (revision) values ('9d5bf74fcee8544d591ac7f97ecf95cc62dd70c4');")
        queries.append("insert into git_log (revision) values ('466a43eebfd5b58171f849c777b6f680832e41de');")
        queries.append("insert into git_log (revision) values ('7cd21180e2330287cf26ea0191ecdbc84526b0c6');")
        queries.append("insert into git_log (revision) values ('1b9fa2a0753c6dc91cb2bc1d875633e720872260');")
        queries.append("insert into git_log (revision) values ('ede00a7db98f209e4e857a38596d167859ec6af7');")
        queries.append("insert into git_log (revision) values ('e1c2f6e23454f03e9bfb7aa3f308aed9ba5d5a10');")
        queries.append("insert into git_log (revision) values ('86af6ce2bc660dd60669903ec279526f9276d5d7');")
        queries.append("insert into git_log (revision) values ('048df9f24981066fc81962770860a7cea1090988');")
        queries.append("insert into git_log (revision) values ('ba037d306c579ff40ad13de8a06e6f4fa0308710');")
        queries.append("insert into git_log (revision) values ('9de951e68c691f1e1c43f1cd15ef4f52e75f5e54');")
        queries.append("insert into git_log (revision) values ('e0f981757591b0c53fcad9e5c2ba362146c85f0f');")
        queries.append("insert into git_log (revision) values ('e63b9cb671f76af84758c148a1e78f701ec593f0');")
        queries.append("insert into git_log (revision) values ('ff70239c112190f5800a9a7dd7634dade789ee97');")
        queries.append("insert into git_log (revision) values ('3d38bdcb1c2bf0bd0c133d9c7843a05c183bc6f1');")
        queries.append("insert into git_log (revision) values ('147b5a655a13822477267b4b3668e24ea2326db5');")
        queries.append("insert into git_log (revision) values ('7c4c1c318e41a96b25a684700d1ec89723b4dc80');")
        queries.append("insert into git_log (revision) values ('d5292c2184fdbc35ea2f49fe416e3f378d808aff');")
        queries.append("insert into git_log (revision) values ('f2bdfe50d5556e89213f11dc035e6ae45f0b7de7');")
        queries.append("insert into git_log (revision) values ('d8cbec1d62d76c3555dc8d69ed1f73640cce3669');")
        queries.append("insert into git_log (revision) values ('eb78b3b3dd502fc387edfb4e5f7903f52a39cb97');")
        queries.append("insert into git_log (revision) values ('30386c48bdd462d0669674d4e9dae171257f67fc');")
        queries.append("insert into git_log (revision) values ('475519e7d4caf977d18730837448828c0b889de1');")
        queries.append("insert into git_log (revision) values ('fb338c0765abb539a4e703de2fcab2549bbb5c39');")
        queries.append("insert into git_log (revision) values ('ece3f0cf7bcac0f2606569010f652f2f93365761');")
        queries.append("insert into git_log (revision) values ('cd741d8bc56e59920ac8a999b1531dc6ac876467');")
        queries.append("insert into git_log (revision) values ('cbe2307c8ac335d92a535d051037e8aff2be8490');")
        queries.append("insert into git_log (revision) values ('08a13095be1780a16e41b82cbb29b7e2f6b9dfae');")
        queries.append("insert into git_log (revision) values ('17af70db5aaea2f313c438aca8d208c218b3cc5a');")
        queries.append("insert into git_log (revision) values ('b852126525ecf25336de3390cbd934685d07ca1e');")
        queries.append("insert into git_log (revision) values ('cf8f7f3b1a3fa37f2b55e0df75ac542842f5b431');")
        queries.append("insert into git_log (revision) values ('deba9b976c5382303a1b586cc28aa86d78c5a216');")
        queries.append("insert into git_log (revision) values ('50a812f411bd5138ff9f2f095398fb907e4f88c6');")
        queries.append("insert into git_log (revision) values ('eede2085b951f144a108d2821bc0dabc1c84b24e');")
        queries.append("insert into git_log (revision) values ('e73ed9814232929d7545f51c6ea9d7afbad55cc2');")
        queries.append("insert into git_log (revision) values ('371197dc7781de1b0daf5647ce98c2de44f336fb');")
        queries.append("insert into git_log (revision) values ('a054c70e7b4cadb9cc2482d73bb1deb65a9ba001');")
        queries.append("insert into git_log (revision) values ('af10edc2e6fb9241dbb6fe27eb0cd3b7d39d8c7c');")
        queries.append("insert into git_log (revision) values ('c91f66d2d1e1bb122d1f5287e79c70288ea70d40');")
        queries.append("insert into git_log (revision) values ('4492c65cc971f58a93816aaf46a9db7f66b6c19b');")
        queries.append("insert into git_log (revision) values ('72eb48bec3e394241e38b6f0aa838c5ed5a98e45');")
        queries.append("insert into git_log (revision) values ('b30317be9089da88819f0d27b3b5580803444af0');")
        queries.append("insert into git_log (revision) values ('a9178c0fd5ae409813c954b31378cdefc7fb5bcb');")
        queries.append("insert into git_log (revision) values ('3fe3501c1fe25ac8f3d9e3a135a16dca0d934f83');")
        queries.append("insert into git_log (revision) values ('b4c8171ce60cbe69f9c6190b4472ef4e0e4e5d2c');")
        queries.append("insert into git_log (revision) values ('4d7eb19b5e12cbe7f106b0272ef87a370969d70e');")
        queries.append("insert into git_log (revision) values ('dbcac37d1456a033c3130ad707254260c86a0d1c');")
        queries.append("insert into git_log (revision) values ('0455447bd96017da7b0852d5f44365236249cb80');")
        queries.append("insert into git_log (revision) values ('12428aafaacca82096c7ce440c8fd4bc2f2385a1');")
        queries.append("insert into git_log (revision) values ('171af08f71b202259623fb9e286069ee1f75dee6');")
        queries.append("insert into git_log (revision) values ('dcc2e2d9c6abe8f6c419c35285d3697978fdc61c');")
        queries.append("insert into git_log (revision) values ('7c02c101cff415adcd3c165d5dcb354729f8956c');")
        queries.append("insert into git_log (revision) values ('84ee767b355d07924f1cd9929807d1aa1155e0fc');")
        queries.append("insert into git_log (revision) values ('4d1cb9e00da8e27e9798afb088a772a33f6a0f89');")
        queries.append("insert into git_log (revision) values ('9fefdabd1a6aed494de490b2271dc99072131db3');")
        queries.append("insert into git_log (revision) values ('d1cfb833efd263628de605b2fc615304de903ff5');")
        queries.append("insert into git_log (revision) values ('85cfa21aa297187348988474a25ec501b8eff11b');")
        queries.append("insert into git_log (revision) values ('c0bd32aaef33435cba077005e4a40143d10f0efa');")
        queries.append("insert into git_log (revision) values ('19d4c6d41c989dd0cd11fa2315c0f71f23725b7d');")
        queries.append("insert into git_log (revision) values ('0b13123a976e61e51e892f7d90d3801d1a868287');")
        queries.append("insert into git_log (revision) values ('e2db73b7372852e9b5e3635b5a4f7e497bf7b4ff');")
        queries.append("insert into git_log (revision) values ('673f6a38e78e45d8980d31d03127887029482e7f');")
        queries.append("insert into git_log (revision) values ('e8f092a936a2effe2fdb719710cd517381517451');")
        queries.append("insert into git_log (revision) values ('c5de4c1e331650143cbed4846e1c622142359d8f');")
        queries.append("insert into git_log (revision) values ('0d6171e15133f34fc7defdc1a008e6c3c386d554');")
        queries.append("insert into git_log (revision) values ('670effb4f6d52836b2b1352dc98026c5f4f700a5');")
        queries.append("insert into git_log (revision) values ('7d4cf3972a4d6cd43ef0acae7c247e48201b678f');")
        queries.append("insert into git_log (revision) values ('22ae86fcd8465e3ee891de15d3bcfeee1894dcf2');")
        queries.append("insert into git_log (revision) values ('d10adbf2e67c3fd2613ade60e7eddb10da3e0af5');")
        queries.append("insert into git_log (revision) values ('b7b08bd7d1e018c1e68a74c112ac3573e93e1067');")
        queries.append("insert into git_log (revision) values ('f3ebffcabf5b0bcab25431719215c28a7ee2a357');")
        queries.append("insert into git_log (revision) values ('e9bc3679354d4d3a277d5f9a559a315df1d2e2fc');")
        queries.append("insert into git_log (revision) values ('683cd4bc8dd37a853ea0428756842308146efca5');")
        queries.append("insert into git_log (revision) values ('996a9f1b1f0b58674098b2390d2c2e61a23d6e69');")
        queries.append("insert into git_log (revision) values ('a95a96034c969233a017e9b3ddb2d9c11059e834');")
        queries.append("insert into git_log (revision) values ('ac00d88423d96c24c82d6540e61043a6d77c8b19');")
        queries.append("insert into git_log (revision) values ('390f4668a2dbe04cfbf59fba026e4646bb7ed5cb');")
        queries.append("insert into git_log (revision) values ('ae4c1122a3985fa96048281750ed00895d70a402');")
        queries.append("insert into git_log (revision) values ('297b370369d6e3011c60a878919b95fa56a9a17a');")
        queries.append("insert into git_log (revision) values ('0d75ae73324b4676c074fac88dd219e931008efc');")
        queries.append("insert into git_log (revision) values ('29f635b477e6b089894e14c6c85cc1926326d8a4');")
        queries.append("insert into git_log (revision) values ('d0ecf95a7b9c578471b333ff9eba9cff44d7699a');")
        queries.append("insert into git_log (revision) values ('952e3a7618429197b3bd4b779a644990baaeee13');")
        queries.append("insert into git_log (revision) values ('d95379a1362d4d09ef841199f85b9da3ea3236f7');")
        queries.append("insert into git_log (revision) values ('fa31f3fab2526baa9acad0257805217ca234e33e');")
        queries.append("insert into git_log (revision) values ('7777daaceda2ca518fba6fcbaba4f2ef027eed2a');")
        queries.append("insert into git_log (revision) values ('4d82457a84e2cea8630283a7033bb0c2cf9cd972');")
        queries.append("insert into git_log (revision) values ('8989067f1bf24e2db6d95435d4551e637480f426');")
        queries.append("insert into git_log (revision) values ('a62f3d5601c3ab95d7b2113cd7958f09cd8075e4');")
        queries.append("insert into git_log (revision) values ('e45c60f4b715dbc73295415ea9d716c795ef694f');")
        queries.append("insert into git_log (revision) values ('ef297548ffdc2c5b4f53f560ba77dcf4801e2b55');")
        queries.append("insert into git_log (revision) values ('911025274725161ea60dfd7dc101b73aea65cfea');")
        queries.append("insert into git_log (revision) values ('e4ad58a2fb718854a3ca2b8b96d5590db027c26c');")
        queries.append("insert into git_log (revision) values ('5c324a7d56a3f3f057f8c15467fb72ae3b73b244');")
        queries.append("insert into git_log (revision) values ('36ec071b68287088831cfd6df82cd6eb8c86ff6e');")
        queries.append("insert into git_log (revision) values ('56ad3231af442e7d724bdd30031328f0bd2d85e8');")
        queries.append("insert into git_log (revision) values ('4fb82374e2cb88f4e4ec5ea02e2a11f43d51f4ec');")
        queries.append("insert into git_log (revision) values ('4875d001509342398d2f9adf1525a513f32d6a37');")
        queries.append("insert into git_log (revision) values ('a713e986442fd540daddf75200ed9286337ac6b1');")
        queries.append("insert into git_log (revision) values ('6b39daff0c2daee0b462534f4808b9d947692622');")
        queries.append("insert into git_log (revision) values ('4be6254f675db525812335c12e3cedee96fe50db');")
        queries.append("insert into git_log (revision) values ('0bf0bad9260d25d64a768ad54f904e458316616d');")
        queries.append("insert into git_log (revision) values ('022d7b50ab33a2413cadfe43a0d6424165075775');")
        queries.append("insert into git_log (revision) values ('50a9e1c14ba12853576f022e9c5d5dd1fd05497d');")
        queries.append("insert into git_log (revision) values ('ef0bb37b0e5bb348610a243bbec1d2a9e4aa95f4');")
        queries.append("insert into git_log (revision) values ('ff9af871f546c9b28b1583d6badb09a356a3e2df');")
        queries.append("insert into git_log (revision) values ('e6f5e1cdc5ef4dcd5299d57ddb4d0eea9e654b1f');")
        queries.append("insert into git_log (revision) values ('b37dbbeec93b7c1a91e4113e30f7153b0d1f79da');")
        queries.append("insert into git_log (revision) values ('0fab94a5fca0d4e67d595e64195d53c7b554cafb');")
        queries.append("insert into git_log (revision) values ('9477a26110f90e5b52460397c6de6e6822c12533');")
        queries.append("insert into git_log (revision) values ('4c33b123c143f416890ca5356d4892b034852b6f');")
        queries.append("insert into git_log (revision) values ('1c93f45ef80571c144417d33b179c982645de75f');")
        queries.append("insert into git_log (revision) values ('4ff5bc861d637d020ce970501b64c82031803810');")
        queries.append("insert into git_log (revision) values ('39715265aaf3ff4defc5eed20033081a5717c849');")
        queries.append("insert into git_log (revision) values ('f7fd820557ef1d1083eced113b8121d6854a351d');")
        queries.append("insert into git_log (revision) values ('4c8de88f095403387173e254225e0aa1ab8c9707');")
        queries.append("insert into git_log (revision) values ('b521e528e4439056c25393fba6a8b7ea0b90fea0');")
        queries.append("insert into git_log (revision) values ('a8ba8aa083a725c44134c9a0bb6a3b257ead28c8');")
        queries.append("insert into git_log (revision) values ('5db4034c69849dcfd4fb0cef3c7b3b4a76576aed');")
        for q in queries:
            cur.execute(q)


def getDatabaseConn(config, init=False):
    DATABASE = os.path.abspath(config['spectraperf_db_path'])
    initDB = False
    # if we already know we are initializing the database skip this step
    if not init and not os.path.isfile(DATABASE):
        initDB = True
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    if not init and initDB:
        InitDatabase(config)
    return con
