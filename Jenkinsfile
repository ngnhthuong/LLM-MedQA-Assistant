pipeline {
  agent any

  environment {
    // -------- GCP / GKE --------
    GCP_PROJECT   = 'aide1-482206'
    GCP_REGION    = 'us-central1'
    GKE_CLUSTER   = 'aide1-gke'

    // -------- Artifact Registry --------
    REGISTRY      = 'us-central1-docker.pkg.dev'
    REPO          = 'llm-medqa'

    // -------- Image versions --------
    RAG_IMAGE     = "${REGISTRY}/${GCP_PROJECT}/${REPO}/rag-orchestrator"
    UI_IMAGE      = "${REGISTRY}/${GCP_PROJECT}/${REPO}/streamlit-ui"
    INGEST_IMAGE  = "${REGISTRY}/${GCP_PROJECT}/${REPO}/qdrant-ingestor"

    IMAGE_TAG     = "${BUILD_NUMBER}"

    // -------- Python --------
    PYTHONUNBUFFERED = '1'
  }

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  stages {

    // ------------------------------------------------------------------
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    // ------------------------------------------------------------------
    stage('Unit Tests (rag-orchestrator)') {
      steps {
        dir('services/rag-orchestrator') {
          sh '''
            python -m venv .venv
            . .venv/bin/activate
            pip install --upgrade pip
            pip install -r requirements.txt
            pytest --cov=app --cov-report=term --cov-fail-under=80
          '''
        }
      }
    }

    // ------------------------------------------------------------------
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

    // ------------------------------------------------------------------
    stage('Build & Push rag-orchestrator') {
      steps {
        dir('services/rag-orchestrator') {
          sh '''
            docker build -t ${RAG_IMAGE}:${IMAGE_TAG} .
            docker push ${RAG_IMAGE}:${IMAGE_TAG}
          '''
        }
      }
    }

    // ------------------------------------------------------------------
    stage('Build & Push streamlit-ui') {
      steps {
        dir('services/streamlit-ui') {
          sh '''
            docker build -t ${UI_IMAGE}:${IMAGE_TAG} .
            docker push ${UI_IMAGE}:${IMAGE_TAG}
          '''
        }
      }
    }

    // ------------------------------------------------------------------
    stage('Build & Push qdrant-ingestor') {
      steps {
        dir('services/qdrant-ingestor') {
          sh '''
            docker build -t ${INGEST_IMAGE}:${IMAGE_TAG} .
            docker push ${INGEST_IMAGE}:${IMAGE_TAG}
          '''
        }
      }
    }

    // ------------------------------------------------------------------
    stage('Helm Dependency Build') {
      steps {
        sh '''
          helm dependency build charts/model-serving
        '''
      }
    }

    // ------------------------------------------------------------------
    stage('Deploy / Upgrade model-serving') {
      steps {
        sh '''
          helm upgrade --install model-serving charts/model-serving \
            --namespace model-serving \
            --create-namespace \
            -f charts/model-serving/values-dev.yaml \
            --set images.rag.tag=${IMAGE_TAG} \
            --set images.ui.tag=${IMAGE_TAG} \
            --set images.ingestor.tag=${IMAGE_TAG}
        '''
      }
    }
  }

  post {
    success {
      echo 'Pipeline succeeded — model-serving deployed to GKE'
    }
    failure {
      echo 'Pipeline failed — check logs above'
    }
  }
}
