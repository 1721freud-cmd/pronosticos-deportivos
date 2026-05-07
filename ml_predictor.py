import sqlite3
import os
import pickle
from datetime import datetime, timedelta
import math
import random

DB_PATH = os.path.join(os.path.dirname(__file__), 'pronosticos.db')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml_model.pkl')

class SimpleMLPredictor:
    """Predictor ML simple sin dependencias externas"""

    def __init__(self):
        self.model = None
        self.load_model()

    def load_model(self):
        """Carga el modelo entrenado si existe"""
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                print("Modelo ML cargado exitosamente")
            except Exception as e:
                print(f"Error cargando modelo: {e}")
                self.model = None
        else:
            print("No hay modelo entrenado, se creará uno nuevo")
            self.model = None

    def save_model(self):
        """Guarda el modelo entrenado"""
        try:
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump(self.model, f)
            print("Modelo ML guardado exitosamente")
        except Exception as e:
            print(f"Error guardando modelo: {e}")

    def get_training_data(self):
        """Obtiene datos de entrenamiento de la base de datos"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

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
            # Features normalizadas
            features = [
                self._normalize_odds(row['home_odds']),
                self._normalize_odds(row['away_odds']),
                self._normalize_odds(row['draw_odds'] if row['draw_odds'] else 3.0),
                row['confidence'] / 100
            ]
            X.append(features)

            # Target: 1 si ganó, 0 si perdió
            y.append(1 if row['status'] == 'won' else 0)

        return X, y

    def _normalize_odds(self, odds):
        """Normaliza cuotas a un rango 0-1"""
        if odds is None:
            return 0.5
        # Cuotas típicas van de 1.0 a 10.0+
        return min(max((odds - 1) / 9, 0), 1)

    def train(self):
        """Entrena el modelo con datos históricos usando un algoritmo simple"""
        X, y = self.get_training_data()

        if X is None or len(X) < 10:
            print("No hay suficientes datos para entrenar")
            return False

        print(f"Entrenando modelo con {len(X)} muestras...")

        # Algoritmo simple: Weighted Average
        # Calcula pesos para cada feature basado en correlación con el resultado
        weights = self._calculate_weights(X, y)

        # Calcular umbral óptimo
        threshold = self._find_optimal_threshold(X, y, weights)

        self.model = {
            'weights': weights,
            'threshold': threshold,
            'trained': True,
            'samples': len(X),
            'accuracy': self._evaluate(X, y, weights, threshold)
        }

        print(f"Precisión: {self.model['accuracy']:.2%}")
        print(f"Umbral óptimo: {threshold:.2f}")

        self.save_model()
        return True

    def _calculate_weights(self, X, y):
        """Calcula pesos para cada feature"""
        n_features = len(X[0])
        weights = [0.0] * n_features

        for i in range(n_features):
            # Calcular correlación simple entre feature y resultado
            feature_values = [x[i] for x in X]
            mean_feature = sum(feature_values) / len(feature_values)
            mean_result = sum(y) / len(y)

            numerator = sum((fv - mean_feature) * (r - mean_result) for fv, r in zip(feature_values, y))
            denominator = math.sqrt(sum((fv - mean_feature) ** 2 for fv in feature_values) *
                                   sum((r - mean_result) ** 2 for r in y))

            if denominator > 0:
                weights[i] = abs(numerator / denominator)
            else:
                weights[i] = 0.0

        # Normalizar pesos
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        return weights

    def _find_optimal_threshold(self, X, y, weights):
        """Encuentra el umbral óptimo para clasificación"""
        scores = [self._score(x, weights) for x in X]

        # Probar diferentes umbrales
        best_threshold = 0.5
        best_accuracy = 0

        for threshold in [i / 100 for i in range(30, 71, 5)]:
            predictions = [1 if score >= threshold else 0 for score in scores]
            correct = sum(1 for p, r in zip(predictions, y) if p == r)
            accuracy = correct / len(y)

            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_threshold = threshold

        return best_threshold

    def _score(self, x, weights):
        """Calcula el score de una muestra"""
        return sum(w * v for w, v in zip(weights, x))

    def _evaluate(self, X, y, weights, threshold):
        """Evalúa el modelo"""
        scores = [self._score(x, weights) for x in X]
        predictions = [1 if score >= threshold else 0 for score in scores]
        correct = sum(1 for p, r in zip(predictions, y) if p == r)
        return correct / len(y)

    def predict(self, home_odds, away_odds, draw_odds, confidence):
        """Predice si un pronóstico será acertado"""
        if self.model is None:
            # Si no hay modelo, usar lógica simple
            return {
                'will_win': confidence >= 60,
                'confidence': confidence,
                'using_ml': False
            }

        # Preparar features
        features = [
            self._normalize_odds(home_odds),
            self._normalize_odds(away_odds),
            self._normalize_odds(draw_odds if draw_odds else 3.0),
            confidence / 100
        ]

        # Calcular score
        score = self._score(features, self.model['weights'])

        # Predecir
        will_win = score >= self.model['threshold']

        return {
            'will_win': will_win,
            'confidence': round(score * 100, 1),
            'using_ml': True,
            'score': round(score, 3)
        }

    def get_feature_importance(self):
        """Obtiene la importancia de cada feature"""
        if self.model is None:
            return None

        feature_names = ['Cuota Local', 'Cuota Visitante', 'Cuota Empate', 'Confianza']
        importance = self.model['weights']

        return dict(zip(feature_names, importance))

# Instancia global del predictor
ml_predictor = SimpleMLPredictor()

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
        'samples': ml_predictor.model.get('samples', 0),
        'accuracy': ml_predictor.model.get('accuracy', 0),
        'feature_importance': ml_predictor.get_feature_importance()
    }
