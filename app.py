# Импортируем необходимые библиотеки Flask для веб-приложения
from flask import Flask, render_template

# Создаем экземпляр приложения Flask
app = Flask(__name__)

# Определяем маршрут для главной страницы
@app.route('/')
def index():
    # Отображаем шаблон index.html
    return render_template('index.html')

# Запускаем приложение в режиме отладки, если файл запущен напрямую
if __name__ == '__main__':
    app.run(debug=True)
