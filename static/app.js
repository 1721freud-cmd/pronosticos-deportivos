// Configuración
const CONFIG = {
    updateInterval: 43200000,
    timeZone: 'America/Argentina/Buenos_Aires',
    animationDuration: 300
};

// Estado global
let allMatches = [];
let currentFilter = 'all';
let lastUpdateTime = null;
let isLoading = false;

// Utilidades
const Utils = {
    getConfidenceBadge(match) {
        if (match.is_very_safe) {
            return '<span class="badge badge-green"><i class="fas fa-shield-alt mr-1"></i>MUY SEGURO</span>';
        } else if (match.is_clear_favorite) {
            return '<span class="badge badge-blue"><i class="fas fa-star mr-1"></i>FAVORITO</span>';
        } else if (match.is_risky) {
            return '<span class="badge badge-red"><i class="fas fa-exclamation-triangle mr-1"></i>RIESGOSO</span>';
        }
        return '';
    },

    getConfidenceColor(confidence) {
        if (confidence >= 75) return 'from-green-500 to-emerald-500';
        if (confidence >= 60) return 'from-blue-500 to-cyan-500';
        if (confidence >= 50) return 'from-yellow-500 to-orange-500';
        return 'from-red-500 to-pink-500';
    },

    getConfidenceTextColor(confidence) {
        if (confidence >= 75) return 'text-green-400';
        if (confidence >= 60) return 'text-blue-400';
        if (confidence >= 50) return 'text-yellow-400';
        return 'text-red-400';
    },

    formatTime(date) {
        return date.toLocaleTimeString('es-AR', {
            timeZone: CONFIG.timeZone,
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    formatRelativeTime(date) {
        const now = new Date();
        const diffMs = date - now;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 24));

        if (diffDays > 0) {
            return `hace ${diffDays} días`;
        } else if (diffHours > 0) {
            return `hace ${diffHours} horas`;
        } else {
            const diffMinutes = Math.floor(diffMs / (1000 * 60));
            return diffMinutes > 0 ? `hace ${diffMinutes} minutos` : 'Ahora mismo';
        }
    },

    showLoading(containerId) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="flex items-center justify-center py-12">
                <div class="loading-spinner"></div>
            </div>
        `;
    },

    showError(containerId, message) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="col-span-full text-center py-12 text-red-400 fade-in">
                <i class="fas fa-exclamation-triangle text-5xl mb-4"></i>
                <p class="text-lg">${message}</p>
            </div>
        `;
    },

    showEmpty(containerId, message) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="col-span-full text-center py-12 text-gray-400 fade-in">
                <i class="fas fa-info-circle text-5xl mb-4"></i>
                <p class="text-lg">${message}</p>
            </div>
        `;
    },

    animateElement(element, animation) {
        element.style.animation = 'none';
        element.offsetHeight;
        element.style.animation = animation;
    }
};

// API
const API = {
    async fetch(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    async getMatches() {
        return this.fetch('/api/matches');
    },

    async getCombinada() {
        return this.fetch('/api/combinada');
    }
};

// Render
const Renderer = {
    updateStats(stats) {
        const elements = {
            'today-count': stats.today_count || 0,
            'tomorrow-count': stats.tomorrow_count || 0,
            'favorites-count': stats.favorites || 0,
            'very-safe-count': stats.very_safe || 0,
            'avg-confidence': (stats.avg_confidence || 0) + '%',
            'last-update': Utils.formatTime(new Date())
        };

        Object.entries(elements).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) {
                el.style.opacity = '0';
                setTimeout(() => {
                    el.textContent = value;
                    el.style.opacity = '1';
                }, 100);
            }
        });
    },

    renderCombinada(combinada) {
        const container = document.getElementById('combinada-container');

        if (combinada.length === 0) {
            Utils.showEmpty(container.id, 'No hay suficientes favoritos claros hoy');
            return;
        }

        container.innerHTML = combinada.map((match, index) => this.createCombinadaCard(match, index)).join('');
    },

    createCombinadaCard(match, index) {
        const delay = index * 0.1;
        const confidenceColor = Utils.getConfidenceColor(match.confidence);

        return `
            <div class="glass-card rounded-xl p-5 border border-yellow-500/30 animate-slide-in" style="animation-delay: ${delay}s">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-3 flex-wrap">
                            <span class="bg-gradient-to-r from-yellow-500 to-orange-500 text-black px-3 py-1 rounded-lg text-sm font-bold">#${index + 1}</span>
                            <span class="text-gray-400 text-sm">${match.date} • ${match.time}</span>
                            ${match.is_today ? '<span class="badge badge-green">HOY</span>' : ''}
                            ${match.sport === 'football' ? '<i class="fas fa-futbol text-green-400"></i>' : '<i class="fas fa-basketball-ball text-orange-400"></i>'}
                            ${match.league ? `<span class="badge badge-blue">${match.league}</span>` : ''}
                        </div>
                        <div class="flex items-center justify-between mb-4">
                            <div class="text-lg font-semibold">${match.home_team}</div>
                            <div class="text-gray-500 font-bold">VS</div>
                            <div class="text-lg font-semibold">${match.away_team}</div>
                        </div>
                        <div class="flex items-center gap-4">
                            <div class="flex-1">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-sm text-gray-400">Confianza</span>
                                    <span class="text-2xl font-bold text-yellow-400">${match.confidence}%</span>
                                </div>
                                <div class="h-3 bg-gray-700 rounded-full overflow-hidden">
                                    <div class="progress-fill ${confidenceColor} rounded-full" style="width: ${match.confidence}%"></div>
                                </div>
                            </div>
                            <div class="text-right">
                                <div class="text-sm text-gray-400">Pronóstico</div>
                                <div class="text-lg font-bold text-white">${match.prediction}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    renderMatches() {
        const container = document.getElementById('matches-container');
        let filteredMatches = this.filterMatches(allMatches, currentFilter);

        if (filteredMatches.length === 0) {
            Utils.showEmpty(container.id, 'No hay partidos disponibles con este filtro');
            return;
        }

        container.innerHTML = filteredMatches.map((match, index) => this.createMatchCard(match, index)).join('');
    },

    createMatchCard(match, index) {
        const delay = index * 0.05;
        const confidenceColor = Utils.getConfidenceColor(match.confidence);
        const confidenceTextColor = Utils.getConfidenceTextColor(match.confidence);
        const borderClass = match.is_very_safe ? 'border-green-500/30' : match.is_clear_favorite ? 'border-blue-500/30' : '';

        return `
            <div class="glass-card rounded-xl p-5 border ${borderClass} animate-slide-in" style="animation-delay: ${delay}s">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2 flex-wrap">
                        ${match.sport === 'football' ? '<i class="fas fa-futbol text-green-400"></i>' : '<i class="fas fa-basketball-ball text-orange-400"></i>'}
                        <span class="text-gray-400 text-sm">${match.date} • ${match.time}</span>
                        ${match.is_today ? '<span class="badge badge-green">HOY</span>' : ''}
                        ${match.is_tomorrow ? '<span class="badge badge-purple">MAÑANA</span>' : ''}
                        ${match.league ? `<span class="badge badge-blue">${match.league}</span>` : ''}
                    </div>
                    ${Utils.getConfidenceBadge(match)}
                </div>

                <div class="flex items-center justify-between mb-4">
                    <div class="text-center flex-1">
                        <div class="font-semibold text-sm mb-1 truncate">${match.home_team}</div>
                        <div class="text-lg font-bold ${match.prediction_team === 'home' ? 'text-green-400' : 'text-gray-400'}">${match.home_odds}</div>
                    </div>
                    <div class="text-center px-3">
                        <div class="text-gray-600 text-xs font-bold">VS</div>
                    </div>
                    <div class="text-center flex-1">
                        <div class="font-semibold text-sm mb-1 truncate">${match.away_team}</div>
                        <div class="text-lg font-bold ${match.prediction_team === 'away' ? 'text-green-400' : 'text-gray-400'}">${match.away_odds}</div>
                    </div>
                </div>

                ${match.draw_odds ? `
                <div class="text-center mb-4 py-2 bg-white/5 rounded-lg">
                    <span class="text-gray-400 text-sm">Empate: </span>
                    <span class="font-bold ${match.prediction_team === 'draw' ? 'text-green-400' : 'text-gray-400'}">${match.draw_odds}</span>
                </div>
                ` : ''}

                <div class="border-t border-gray-700/30 pt-4">
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-sm text-gray-400">Nivel de Confianza</span>
                        <span class="text-xl font-bold ${confidenceTextColor}">${match.confidence}%</span>
                    </div>
                    <div class="h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div class="progress-fill ${confidenceColor} rounded-full" style="width: ${match.confidence}%"></div>
                    </div>
                    <div class="mt-2 flex items-center justify-between">
                        <span class="text-sm text-gray-400">Pronóstico: </span>
                        <span class="font-medium ${confidenceTextColor}">${match.prediction}</span>
                    </div>
                </div>
            </div>
        `;
    },

    filterMatches(matches, filter) {
        const filters = {
            'today': m => m.is_today,
            'tomorrow': m => m.is_tomorrow,
            'football': m => m.sport === 'football',
            'basketball': m => m.sport === 'basketball',
            'favorites': m => m.is_clear_favorite,
            'very-safe': m => m.is_very_safe,
            'premier': m => m.league === 'Premier League',
            'laliga': m => m.league === 'La Liga',
            'seriea': m => m.league === 'Serie A',
            'bundesliga': m => m.league === 'Bundesliga',
            'ucl': m => m.league === 'Champions League',
            'argentina': m => m.league === 'Liga Argentina'
        };

        return filters[filter] ? matches.filter(filters[filter]) : matches;
    },

    updateFilterButtons(filter) {
        document.querySelectorAll('.filter-btn').forEach(btn => {
            const isActive = btn.dataset.filter === filter;
            btn.classList.toggle('active', isActive);
        });
    }
};

// Controlador
const App = {
    async init() {
        try {
            await this.loadData();
            this.scheduleNextUpdate();
        } catch (error) {
            console.error('Error initializing app:', error);
            Utils.showError('matches-container', 'Error al cargar los datos');
        }
    },

    async loadData() {
        if (isLoading) return;
        isLoading = true;

        Utils.showLoading('matches-container');
        Utils.showLoading('combinada-container');

        try {
            const [matchesData, combinadaData] = await Promise.all([
                API.getMatches(),
                API.getCombinada()
            ]);

            allMatches = matchesData.matches;
            lastUpdateTime = new Date();
            Renderer.updateStats(matchesData.stats);
            Renderer.renderMatches();
            Renderer.renderCombinada(combinadaData.combinada);
        } finally {
            isLoading = false;
        }
    },

    filterMatches(filter) {
        currentFilter = filter;
        Renderer.updateFilterButtons(filter);
        Renderer.renderMatches();
    },

    refreshData() {
        if (isLoading) return;
        this.loadData();
    },

    scheduleNextUpdate() {
        const now = new Date();
        const argentinaTime = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + (3 * 3600000));
        const hours = argentinaTime.getHours();

        let nextUpdateHours;
        if (hours < 12) {
            nextUpdateHours = 12 - hours;
        } else {
            nextUpdateHours = 24 - hours;
        }

        const nextUpdateMinutes = 60 - argentinaTime.getMinutes();
        const nextUpdateMs = (nextUpdateHours * 60 * 60 * 1000) + (nextUpdateMinutes * 60 * 1000);

        console.log(`Próxima actualización a las ${new Date(now.getTime() + nextUpdateMs).toLocaleTimeString('es-AR', { timeZone: CONFIG.timeZone })} (hora argentina)`);

        setTimeout(() => {
            this.loadData();
            this.scheduleNextUpdate();
        }, nextUpdateMs);
    }
};

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

// Funciones globales para HTML
window.filterMatches = (filter) => App.filterMatches(filter);
window.refreshData = () => App.refreshData();
