"""
Service d'analyse et de prédiction des visites
Utilise Machine Learning pour analyser les patterns de visite et prédire les visites futures
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import logging
from typing import Dict, List, Tuple, Optional
import json

class VisitAnalyticsService:
    """Service pour l'analyse et la prédiction des visites"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.is_trained = False

    def get_visit_stats(self, db_session) -> Dict:
        """Récupère les statistiques de visite depuis la base de données"""
        try:
            from models.visit_log import VisitLog

            # Récupérer toutes les visites
            visits = db_session.query(VisitLog).all()

            if not visits:
                return {
                    'total_visits': 0,
                    'unique_visitors': 0,
                    'visits_today': 0,
                    'visits_this_week': 0,
                    'visits_this_month': 0,
                    'daily_data': [],
                    'hourly_data': [],
                    'popular_pages': [],
                    'debug_info': 'Aucune visite enregistrée'
                }

            # Convertir en DataFrame pour faciliter l'analyse
            data = []
            for visit in visits:
                data.append({
                    'timestamp': visit.timestamp,
                    'ip_address': visit.ip_address,
                    'url': visit.url,
                    'user_agent': visit.user_agent,
                    'referrer': visit.referrer
                })

            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Debug : analyser la répartition des dates
            unique_dates = df['timestamp'].dt.date.unique()
            date_counts = df.groupby(df['timestamp'].dt.date).size()

            # Calculer les statistiques
            now = datetime.now()
            today = now.date()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            stats = {
                'total_visits': len(df),
                'unique_visitors': df['ip_address'].nunique(),
                'visits_today': len(df[df['timestamp'].dt.date == today]),
                'visits_this_week': len(df[df['timestamp'] >= week_ago]),
                'visits_this_month': len(df[df['timestamp'] >= month_ago]),
                'daily_data': self._get_daily_data(df),
                'hourly_data': self._get_hourly_data(df),
                'popular_pages': self._get_popular_pages(df),
                'debug_info': {
                    'total_visits': len(visits),
                    'unique_days': len(unique_dates),
                    'date_range': f"Du {min(unique_dates)} au {max(unique_dates)}",
                    'visits_per_day': date_counts.to_dict()
                }
            }

            return stats

        except Exception as e:
            self.logger.error(f"Erreur lors du calcul des statistiques: {e}")
            return {'debug_info': f'Erreur: {str(e)}'}

    def _get_daily_data(self, df: pd.DataFrame) -> List[Dict]:
        """Agrège les données par jour"""
        daily = df.groupby(df['timestamp'].dt.date).size().reset_index()
        daily.columns = ['date', 'visits']
        daily['date'] = daily['date'].astype(str)
        return daily.to_dict('records')

    def _get_hourly_data(self, df: pd.DataFrame) -> List[Dict]:
        """Agrège les données par heure de la journée"""
        hourly = df.groupby(df['timestamp'].dt.hour).size().reset_index()
        hourly.columns = ['hour', 'visits']
        return hourly.to_dict('records')

    def _get_popular_pages(self, df: pd.DataFrame, limit: int = 10) -> List[Dict]:
        """Récupère les pages les plus visitées"""
        popular = df.groupby('url').size().reset_index()
        popular.columns = ['url', 'visits']
        popular = popular.sort_values('visits', ascending=False).head(limit)
        return popular.to_dict('records')

    def prepare_prediction_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prépare les features pour la prédiction ML"""
        try:
            # Agrégation quotidienne
            daily_visits = df.groupby(df['timestamp'].dt.date).size().reset_index()
            daily_visits.columns = ['date', 'visits']
            daily_visits['date'] = pd.to_datetime(daily_visits['date'])
            daily_visits = daily_visits.sort_values('date')

            if len(daily_visits) < 7:  # Pas assez de données
                self.logger.warning(f"Pas assez de données quotidiennes: {len(daily_visits)} jours (minimum 7)")
                return np.array([]), np.array([])

            # Créer des features temporelles
            daily_visits['day_of_week'] = daily_visits['date'].dt.dayofweek
            daily_visits['day_of_month'] = daily_visits['date'].dt.day
            daily_visits['is_weekend'] = daily_visits['day_of_week'].isin([5, 6]).astype(int)

            # Features de tendance (moyennes mobiles)
            daily_visits['visits_ma3'] = daily_visits['visits'].rolling(window=3, min_periods=1).mean()
            daily_visits['visits_ma7'] = daily_visits['visits'].rolling(window=7, min_periods=1).mean()

            # Sélectionner les features
            features = ['day_of_week', 'day_of_month', 'is_weekend', 'visits_ma3', 'visits_ma7']
            X = daily_visits[features].fillna(0).values
            y = daily_visits['visits'].values

            self.logger.info(f"Features préparées: {X.shape[0]} échantillons, {X.shape[1]} features")
            return X, y

        except Exception as e:
            self.logger.error(f"Erreur lors de la préparation des features: {e}")
            return np.array([]), np.array([])

    def train_prediction_model(self, db_session) -> Dict:
        """Entraîne le modèle de prédiction des visites"""
        try:
            from models.visit_log import VisitLog

            # Récupérer les données d'entraînement
            visits = db_session.query(VisitLog).all()

            if len(visits) < 14:  # Besoin d'au moins 2 semaines de données
                return {
                    'success': False,
                    'message': f'Pas assez de données pour entraîner le modèle (minimum 14 jours, actuellement {len(visits)} visites)'
                }

            # Convertir en DataFrame
            data = []
            for visit in visits:
                data.append({
                    'timestamp': visit.timestamp,
                    'ip_address': visit.ip_address,
                    'url': visit.url
                })

            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Préparer les features
            X, y = self.prepare_prediction_features(df)

            if len(X) == 0 or len(y) == 0:
                unique_days = df['timestamp'].dt.date.nunique()
                return {
                    'success': False,
                    'message': f'Données insuffisantes pour l\'entraînement (seulement {unique_days} jours uniques)'
                }

            # Vérifier la cohérence des données
            if X.shape[0] != y.shape[0]:
                return {
                    'success': False,
                    'message': f'Incohérence des données: {X.shape[0]} features vs {y.shape[0]} targets'
                }

            # Normaliser les features
            X_scaled = self.scaler.fit_transform(X)

            # Entraîner le modèle
            self.model.fit(X_scaled, y)
            self.is_trained = True

            # Calculer les métriques de performance
            y_pred = self.model.predict(X_scaled)
            mse = mean_squared_error(y, y_pred)
            r2 = r2_score(y, y_pred)

            self.logger.info(f"Modèle entraîné - MSE: {mse:.2f}, R²: {r2:.2f}")

            return {
                'success': True,
                'message': 'Modèle entraîné avec succès',
                'metrics': {
                    'mse': float(mse),
                    'r2': float(r2),
                    'training_samples': len(X)
                }
            }

        except Exception as e:
            self.logger.error(f"Erreur lors de l'entraînement: {e}")
            return {
                'success': False,
                'message': f'Erreur lors de l\'entraînement: {str(e)}'
            }

    def predict_future_visits(self, days_ahead: int = 7) -> List[Dict]:
        """Prédit les visites futures"""
        try:
            if not self.is_trained:
                return []

            predictions = []
            base_date = datetime.now().date()

            for i in range(1, days_ahead + 1):
                future_date = base_date + timedelta(days=i)

                # Créer les features pour cette date
                features = [
                    future_date.weekday(),  # day_of_week
                    future_date.day,        # day_of_month
                    1 if future_date.weekday() >= 5 else 0,  # is_weekend
                    50,  # visits_ma3 (valeur par défaut)
                    45   # visits_ma7 (valeur par défaut)
                ]

                X_future = np.array([features])
                X_future_scaled = self.scaler.transform(X_future)

                predicted_visits = self.model.predict(X_future_scaled)[0]
                predicted_visits = max(0, int(predicted_visits))  # Pas de visites négatives

                predictions.append({
                    'date': future_date.strftime('%Y-%m-%d'),
                    'predicted_visits': predicted_visits,
                    'confidence': 'medium'  # Pourrait être calculé plus précisément
                })

            return predictions

        except Exception as e:
            self.logger.error(f"Erreur lors de la prédiction: {e}")
            return []

    def generate_insights(self, stats: Dict) -> List[str]:
        """Génère des insights automatiques basés sur les données"""
        insights = []

        try:
            if stats.get('total_visits', 0) > 0:
                # Analyse de la croissance
                daily_data = stats.get('daily_data', [])
                if len(daily_data) >= 7:
                    recent_avg = np.mean([d['visits'] for d in daily_data[-7:]])
                    previous_avg = np.mean([d['visits'] for d in daily_data[-14:-7]]) if len(daily_data) >= 14 else recent_avg

                    if recent_avg > previous_avg * 1.1:
                        insights.append("📈 Croissance des visites : +{:.1f}% cette semaine".format((recent_avg/previous_avg - 1) * 100))
                    elif recent_avg < previous_avg * 0.9:
                        insights.append("📉 Baisse des visites : -{:.1f}% cette semaine".format((1 - recent_avg/previous_avg) * 100))

                # Analyse des heures de pointe
                hourly_data = stats.get('hourly_data', [])
                if hourly_data:
                    peak_hour = max(hourly_data, key=lambda x: x['visits'])
                    insights.append(f"⏰ Heure de pointe : {peak_hour['hour']}h avec {peak_hour['visits']} visites")

                # Analyse des pages populaires
                popular_pages = stats.get('popular_pages', [])
                if popular_pages:
                    top_page = popular_pages[0]
                    insights.append(f"🔥 Page la plus visitée : {top_page['url']} ({top_page['visits']} visites)")

        except Exception as e:
            self.logger.error(f"Erreur lors de la génération d'insights: {e}")

        return insights
