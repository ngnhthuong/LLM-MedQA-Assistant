pipeline {
  agent any

  environment {
    // ---------------- GCP / GKE ----------------
    GCP_PROJECT   = 'aide1-482206'
    GCP_REGION    = 'us-central1'
    GKE_CLUSTER   = 'gke-medqa-autopilot'

    // ---------------- Artifact Registry ----------------
    REGISTRY      = 'us-central1-docker.pkg.dev'
    REPO          = 'llm-medqa'

    // ---------------- Image names ----------------
    RAG_IMAGE     = "${REGISTRY}/${GCP_PROJECT}/${REPO}/rag-orchestrator"
    UI_IMAGE      = "${REGISTRY}/${GCP_PROJECT}/${REPO}/streamlit-ui"
    INGEST_IMAGE  = "${REGISTRY}/${GCP_PROJECT}/${REPO}/qdrant-ingestor"

    // ---------------- Image versions (SOURCE OF TRUTH) ----------------
    // Bump these intentionally when you want new releases
    RAG_VERSION   = '0.4.7'
    UI_VERSION    = '0.2.2'
    INGEST_VERSION= '0.1.2'

    // ---------------- Helm ----------------
    HELM_RELEASE  = 'model-serving'
    HELM_NAMESPACE= 'model-serving'

    PYTHONUNBUFFERED = '1'
  }

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  stages {

    // --------------------------------------------------
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    // --------------------------------------------------
    stage('Unit Tests (rag-orchestrator)') {
      steps {
        dir('services/rag-orchestrator') {
          sh '''
            python3 -m venv .venv
            . .venv/bin/activate
            pip install --upgrade pip
            pip install -r requirements.txt
            pytest --cov=app --cov-report=term --cov-fail-under=80
          '''
        }
      }
    }
    stage('Static Code Analysis - SonarQube') {
      steps {
        dir('services/rag-orchestrator') {
          withSonarQubeEnv('SonarCloud') {
            sh '''
              set -e
              export SONAR_SCANNER_VERSION=8.0.1.6346
              export SONAR_SCANNER_HOME=$HOME/.sonar/sonar-scanner-$SONAR_SCANNER_VERSION-linux-x64

              curl --create-dirs -sSLo $HOME/.sonar/sonar-scanner.zip https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-$SONAR_SCANNER_VERSION-linux-x64.zip

              unzip -o $HOME/.sonar/sonar-scanner.zip -d $HOME/.sonar/
              export PATH=$SONAR_SCANNER_HOME/bin:$PATH

              sonar-scanner \
                -Dsonar.organization=lehuyphuong \
                -Dsonar.projectKey=lehuyphuong_LLM-MedQA-Assistant
            '''
          }
        }
      }
    }

    stage('IaC Security Scan - Checkov') {
      steps {
        sh '''
          docker run --rm \
            -v "$PWD:/workspace" \
            bridgecrew/checkov:latest \
            -d /workspace \
            --framework helm,terraform \
            --quiet
        '''
      }
    }

    stage('Quality Gate') {
      steps {
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }

    // --------------------------------------------------
    stage('Authenticate to GCP & GKE') {
      steps {
        withCredentials([
          file(credentialsId: 'gcp-jenkins-sa', variable: 'GCP_KEY')
        ]) {
          sh '''
            gcloud auth activate-service-account --key-file="$GCP_KEY"
            gcloud config set project ${GCP_PROJECT}
            gcloud auth configure-docker ${REGISTRY} -q
            gcloud container clusters get-credentials ${GKE_CLUSTER} \
              --region ${GCP_REGION}
          '''
        }
      }
    }

    // --------------------------------------------------
    stage('Build & Push rag-orchestrator') {
      steps {
        dir('services/rag-orchestrator') {
          sh '''
            docker build -t ${RAG_IMAGE}:${RAG_VERSION} .
            docker push ${RAG_IMAGE}:${RAG_VERSION}
          '''
        }
      }
    }

    // --------------------------------------------------
    stage('Build & Push streamlit-ui') {
      steps {
        dir('services/streamlit-ui') {
          sh '''
            docker build -t ${UI_IMAGE}:${UI_VERSION} .
            docker push ${UI_IMAGE}:${UI_VERSION}
          '''
        }
      }
    }

    // --------------------------------------------------
    stage('Build & Push qdrant-ingestor') {
      steps {
        dir('services/qdrant-ingestor') {
          sh '''
            docker build -t ${INGEST_IMAGE}:${INGEST_VERSION} .
            docker push ${INGEST_IMAGE}:${INGEST_VERSION}
          '''
        }
      }
    }

    // --------------------------------------------------
    stage('Helm delete model-serving') {
      steps {
        sh '''
          helm uninstall model-serving -n model-serving
        '''
      }
    }

    // --------------------------------------------------
    stage('Helm Dependency Build') {
      steps {
        sh '''
          helm dependency build charts/model-serving
        '''
      }
    }

    // --------------------------------------------------
    stage('Deploy / Upgrade model-serving') {
      steps {
        sh '''
          helm upgrade --install ${HELM_RELEASE} charts/model-serving \
            --namespace ${HELM_NAMESPACE} \
            --create-namespace \
            -f charts/model-serving/values-dev.yaml \
            --set images.rag.tag=${RAG_VERSION} \
            --set images.ui.tag=${UI_VERSION} \
            --set images.ingestor.tag=${INGEST_VERSION}
        '''
      }
    }
  }

  post {
    success {
      echo 'CI/CD pipeline succeeded — model-serving deployed to GKE'
    }
    failure {
      echo 'CI/CD pipeline failed — check logs above'
    }
  }
}
