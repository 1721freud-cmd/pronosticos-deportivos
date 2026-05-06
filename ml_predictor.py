import sqlite3
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import os
import pickle
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'pronosticos.db')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml_model.pkl')
SCALER_PATH = os.path.join(os.path.dirname(__file__), 'scaler.pkl')

class MLPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.load_model()

    def load_model(self):
        """Carga el modelo entrenado si existe"""
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            try:
                with open(MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                with open(SCALER_PATH, 'rb') as f:
                    self.scaler = pickle.load(f)
                print("Modelo ML cargado exitosamente")
            except Exception as e:
                print(f"Error cargando modelo: {e}")
                self.model = None
        else:
            print("No hay modelo entrenado, se creará uno nuevo")
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)

    def save_model(self):
        """Guarda el modelo entrenado"""
        try:
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump(self.model, f)
            with open(SCALER_PATH, 'wb') as f:
                pickle.dump(self.scaler, f)
            print("Modelo ML guardado exitosamente")
        except Exception as e:
            print(f"Error guardando modelo: {e}")

    def get_training_data(self):
        """Obtiene datos de entrenamiento de la base de datos"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Obtener pronósticos con resultados
        cursor.execute('''
            SELECT home_odds, away_odds, draw_odds, confidence,
                   prediction_team, status
            FROM pronosticos
            WHERE status IN ('won', 'lost')
            AND home_odds IS NOT NULL
            AND away_odds IS NOT NULL
        ''')

        results = cursor.fetchall()
        conn.close()

        if len(results) < 10:
            print("No hay suficientes datos para entrenar (mínimo 10)")
            return None, None

        X = []
        y = []

        for row in results:
            # Features: cuotas y confianza
            features = [
                row['home_odds'],
                row['away_odds'],
                row['draw_odds'] if row['draw_odds'] else 0,
                row['confidence']
            ]
            X.append(features)

            # Target: 1 si ganó, 0 si perdió
            y.append(1 if row['status'] == 'won' else 0)

        return np.array(X), np.array(y)

    def train(self):
        """Entrena el modelo con datos históricos"""
        X, y = self.get_training_data()

        if X is None or len(X) < 10:
            print("No hay suficientes datos para entrenar")
            return False

        print(f"Entrenando modelo con {len(X)} muestras...")

        # Dividir datos
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Escalar features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Entrenar modelo
        self.model.fit(X_train_scaled, y_train)

        # Evaluar
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)

        print(f"Precisión entrenamiento: {train_score:.2%}")
        print(f"Precisión prueba: {test_score:.2%}")

        # Guardar modelo
        self.save_model()

        return True

    def predict(self, home_odds, away_odds, draw_odds, confidence):
        """Predice si un pronóstico será acertado"""
        if self.model is None:
            # Si no hay modelo, usar lógica simple
            return confidence >= 60

        # Preparar features
        features = np.array([[home_odds, away_odds, draw_odds or 0, confidence]])
        features_scaled = self.scaler.transform(features)

        # Predecir
        prediction = self.model.predict(features_scaled)[0]
        probability = self.model.predict_proba(features_scaled)[0][1]

        return {
            'will_win': bool(prediction),
            'confidence': round(probability * 100, 1),
            'using_ml': True
        }

    def get_feature_importance(self):
        """Obtiene la importancia de cada feature"""
        if self.model is None:
            return None

        feature_names = ['Cuota Local', 'Cuota Visitante', 'Cuota Empate', 'Confianza']
        importance = self.model.feature_importances_

        return dict(zip(feature_names, importance))

# Instancia global del predictor
ml_predictor = MLPredictor()

def train_ml_model():
    """Entrena el modelo ML"""
    return ml_predictor.train()

def predict_with_ml(home_odds, away_odds, draw_odds, confidence):
    """Hace una predicción usando ML"""
    return ml_predictor.predict(home_odds, away_odds, draw_odds, confidence)

def get_ml_stats():
    """Obtiene estadísticas del modelo ML"""
    if ml_predictor.model is None:
        return None

    return {
        'model_trained': True,
        'feature_importance': ml_predictor.get_feature_importance()
    }
