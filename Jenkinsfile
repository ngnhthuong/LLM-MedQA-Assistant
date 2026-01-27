pipeline {
  agent any

  environment {
    PROJECT_ID      = "aide1-482206"
    REGION          = "us-central1"
    REGISTRY        = "us-central1-docker.pkg.dev"
    REPO            = "llm-medqa"

    // Image versions (change to bump)
    RAG_VERSION     = "0.1.8"
    STREAMLIT_VER   = "0.2.0"
    INGESTOR_VER    = "0.1.2"

    // Helm
    HELM_NAMESPACE  = "model-serving"
    HELM_RELEASE    = "model-serving"
  }

  stages {

    stage("Checkout") {
      steps {
        checkout scm
      }
    }

    stage("Unit Tests (rag-orchestrator)") {
      steps {
        dir("services/rag-orchestrator") {
          sh """
            python3 -m venv .venv
            . .venv/bin/activate
            pip install -r requirements.txt
            pip install pytest pytest-cov
            pytest --cov=app --cov-fail-under=80
          """
        }
      }
    }

    stage("Build & Push rag-orchestrator") {
      steps {
        dir("services/rag-orchestrator") {
          sh """
            docker build -t ${REGISTRY}/${PROJECT_ID}/${REPO}/rag-orchestrator:${RAG_VERSION} .
            docker push ${REGISTRY}/${PROJECT_ID}/${REPO}/rag-orchestrator:${RAG_VERSION}
          """
        }
      }
    }

    stage("Build & Push streamlit-ui") {
      steps {
        dir("services/streamlit-ui") {
          sh """
            docker build -t ${REGISTRY}/${PROJECT_ID}/${REPO}/streamlit-ui:${STREAMLIT_VER} .
            docker push ${REGISTRY}/${PROJECT_ID}/${REPO}/streamlit-ui:${STREAMLIT_VER}
          """
        }
      }
    }

    stage("Build & Push qdrant-ingestor") {
      steps {
        dir("services/qdrant-ingestor") {
          sh """
            docker build -t ${REGISTRY}/${PROJECT_ID}/${REPO}/qdrant-ingestor:${INGESTOR_VER} .
            docker push ${REGISTRY}/${PROJECT_ID}/${REPO}/qdrant-ingestor:${INGESTOR_VER}
          """
        }
      }
    }

    stage("Helm Dependency Build") {
      steps {
        sh """
          helm dependency build charts/model-serving
        """
      }
    }

    stage("Deploy / Upgrade model-serving") {
      steps {
        sh """
          helm upgrade --install ${HELM_RELEASE} charts/model-serving \
            -n ${HELM_NAMESPACE} \
            -f charts/model-serving/values-dev.yaml \
            --create-namespace
        """
      }
    }
  }

  post {
    success {
      echo " CI/CD pipeline completed successfully"
    }
    failure {
      echo " Pipeline failed — check test coverage or build logs"
    }
  }
}
