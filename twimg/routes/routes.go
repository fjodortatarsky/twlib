package routes

import (
	"fmt"
	"net/http"
)

func Default(w http.ResponseWriter, r *http.Request) {
        http.Error(w, "Page not found", 404)
}

func GetImage(w http.ResponseWriter, r *http.Request) {
        id := r.PathValue("id")
	fmt.Fprintf(w, "запрошена картинка с id %s", id)
}

func UploadImage(w http.ResponseWriter, r *http.Request) {
        
}
