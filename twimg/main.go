package main

import (
	"fmt"
	"net/http"
	"twimg/routes"
)

func main() {

	mux := http.NewServeMux()

	mux.HandleFunc("GET /getimage/{id}", routes.GetImage)

	fmt.Println("Сервер запущен")
	if err := http.ListenAndServe(":8081", mux); err != nil {
		fmt.Println("Ошибка: ", err)
	}
}
