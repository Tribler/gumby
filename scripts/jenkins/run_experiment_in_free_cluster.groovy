
def gitCheckout(url, branch, targetDir=''){
  if (targetDir == '') {
    targetDir = (url =~ '.*/(.+).git')[0][1]
  }
  echo "cloning ${url} to ${targetDir} and checking out branch: ${branch}"

  checkout([$class: 'GitSCM',
            userRemoteConfigs: [[url: url]],
            branches: [[name: branch]],

            doGenerateSubmoduleConfigurations: false,
            extensions: [[$class: 'CloneOption',
                          noTags: false,
                          reference: '',
                          shallow: true],

                         [$class: 'SubmoduleOption',
                          disableSubmodules: false,
                          recursiveSubmodules: true,
                          reference: '',
                          trackingSubmodules: false],

                         [$class: 'RelativeTargetDirectory',
                          relativeTargetDir: targetDir],

                         [$class: 'CleanCheckout'],

                         [$class: 'CleanBeforeCheckout']],
            submoduleCfg: [],
           ])

}

def checkoutGumby() {
  gitCheckout('https://github.com/whirm/gumby.git', '*/devel')
}

def runOnFreeCluster(experimentConf){
  //def experimentConf = env.EXPERIMENT_CONF
  // stage 'Checkout gumby'
  // checkoutGumby()

  stage 'Find a free cluster'

  def experimentName
  def clusterName
  node('master') {  def confFile = readFile(experimentConf).replaceAll(/#.*/,"")
    def configObject = new ConfigSlurper().parse(confFile)
    def neededNodes = configObject.das4_node_amount
    experimentName = configObject.experiment_name
    configObject = null

    try {
      neededNodes = "${NODES}"
    } catch (groovy.lang.MissingPropertyException err) {
      echo "NODES env var not passed, using config file value"
    }

    sh "gumby/scripts/find_free_cluster.sh ${neededNodes}"
    clusterName = readFile('cluster.txt')
  }

  stage "Run ${experimentName}"

  node(clusterName) {
    try {

      unstash "experiment_workdir"

      // stage 'Check out Gumby'
      // checkoutGumby()

      // stage 'Check out Tribler'
      // gitCheckout('https://github.com/Tribler/tribler.git', '*/devel')

      sh """
gumby/scripts/build_virtualenv.sh
source ~/venv/bin/activate

./gumby/run.py ${experimentConf}
"""
    } finally {
      stash includes: 'output/**', name: 'experiment_results'
    }
  }
}

runOnFreeCluster(env.EXPERIMENT_CONF)
