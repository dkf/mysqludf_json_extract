#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <mysql.h>

#include <yajl/yajl_parse.h>

#if 0
#define OUT(f, ...) {			       \
    if (json_state->current == NULL) {	       \
      printf("d: d, ad: d\t"f, ##__VA_ARGS__); \
    } else {				       \
      printf("d: %d, ad: %d, n: %s\t"f,	       \
	     json_state->current->depth,       \
	     json_state->current->arr_depth,   \
	     json_state->current->el,	       \
	     ##__VA_ARGS__);		       \
    }					       \
  }
#define PARSE_TREE(el) printf("->%s", el)
#define PARSE_TREE_END(el) printf("\n")
#else 
#define OUT(f, ...)
#define PARSE_TREE(el)
#define PARSE_TREE_END(el)
#endif

struct json_el {
  char *el;
  int el_len;
  int depth;
  int arr_depth;
  struct json_el *next;
  struct json_el *prev;
};

struct json_state {
  int done;
  char *res;
  int res_len;
  struct json_el *head;
  struct json_el *current;
  struct json_el *last;
};

static yajl_parser_config parser_config = { 1, 0 };

int handle_null(void *ctx) {
  struct json_state *json_state = ctx;
  OUT("NULL\n");
  if (json_state->done == 1) {
    strncpy(json_state->res, "null", 4);
    json_state->res_len = 4;
    return 0;
  } else if (json_state->current->arr_depth > 0) {
    return 1;
  } else {
    json_state->current->depth--;
  }
  return 1;
}

int handle_bool(void *ctx, int b) {
  struct json_state *json_state = ctx;
  OUT("BOOL %d\n", b);
  if (json_state->done == 1) {
    if (b) {
      strncpy(json_state->res, "true", 4);
      json_state->res_len = 4;
    } else {
      strncpy(json_state->res, "false", 5);
      json_state->res_len = 5;
    }
    return 0;
  } else if (json_state->current->arr_depth > 0) {
    return 1;
  } else {
    json_state->current->depth--;
  }
  return 1;
}

int handle_num(void *ctx, const char *num, unsigned int len) {
  struct json_state *json_state = ctx;
  OUT("NUM\n");
  if (json_state->done == 1) {
    if (len > 255) {
      len = 255;
    }
    strncpy(json_state->res, num, len);
    json_state->res_len = len;
    return 0;
  } else if (json_state->current->arr_depth > 0) {
    return 1;
  } else {
    json_state->current->depth--;
  }
  return 1;
}

int handle_string(void *ctx, const unsigned char *s, unsigned int len) {
  struct json_state *json_state = ctx;
  OUT("STRING\n");
  if (len > 255) {
    len = 255;
  }
  if (json_state->done == 1) {
    strncpy(json_state->res, (const char *) s, len);
    json_state->res_len = len;
    return 0;
  }
  if (json_state->current->arr_depth > 0) {
    return 1;
  }
  json_state->current->depth--;
  return 1;
}

int handle_start_map(void *ctx) {
  struct json_state *json_state = ctx;
  OUT("START_MAP\n");
  if (json_state->done == 1) {
    json_state->done = 0;
    return 0;
  }
  return 1;
}

int handle_map_key(void *ctx, const unsigned char *s, unsigned int len) {
  struct json_state *json_state = ctx;
  OUT("MAP_KEY\n");
  if (json_state->done == 1) {
    // shouldn't happen
    json_state->done = 0;
    return 0;
  }
  if (json_state->current->arr_depth > 0) {
    return 1;
  }
  if (json_state->current->depth == 0 && 
      json_state->current->el_len == len && 
      strncmp((const char *) s, json_state->current->el, len) == 0) {
    json_state->current = json_state->current->next;
    if (json_state->current == NULL) {
      json_state->done = 1;
    }

  } else {
    json_state->current->depth++;
  }
  return 1;
}

int handle_end_map(void *ctx) {
  struct json_state *json_state = ctx;
  OUT("END_MAP\n");
  if (json_state->done == 1) {
    // shouldn't happen
    json_state->done = 0;
    return 0;
  } else if (json_state->current->arr_depth > 0) {
    return 1;
  }
  json_state->current->depth--;
  return 1;
}

int handle_start_array(void *ctx) {
  struct json_state *json_state = ctx;
  OUT("START_ARRAY\n");
  if (json_state->done == 1) {
    json_state->done = 0;
    return 0;
  }
  json_state->current->arr_depth++;
  return 1;
}

int handle_end_array(void *ctx) {
  struct json_state *json_state = ctx;
  OUT("END_ARRAY\n");
  if (json_state->done == 1) {
    // shouldn't happen
    json_state->done = 0;
    return 0;
  }
  json_state->current->arr_depth--;
  if (json_state->current->arr_depth == 0) {
    json_state->current->depth--;
  }
  return 1;
}

static yajl_callbacks callbacks = {
  handle_null,
  handle_bool,
  NULL,
  NULL,
  handle_num,
  handle_string,
  handle_start_map,
  handle_map_key,
  handle_end_map,
  handle_start_array,
  handle_end_array
};

my_bool json_extract_init(UDF_INIT *initid, UDF_ARGS *args, char *message) {
  if (args->arg_count != 2) {
    strcpy(message, "json_extract() takes two arguments");
    return 1;
  }
  if (args->arg_type[0] != STRING_RESULT) {
    strcpy(message, "json_extract()'s first argument must be a string");
    return 1;
  }
  if (args->arg_type[1] != STRING_RESULT) {
    strcpy(message, "json_extract()'s second argument must be a string");
    return 1;
  }
  if (args->args[0] == 0) {
    strcpy(message, "json_extract()'s first argument must be constant and cannot be null");
    return 1;
  }
  if (args->lengths[0] == 0) {
    strcpy(message, "json_extract()'s first argument can't be empty");
    return 1;
  }

  initid->maybe_null = 1;
  initid->const_item = 1;

  struct json_state *json_state = calloc(1, sizeof(struct json_state));

  json_state->head = calloc(1, sizeof(struct json_el));
  json_state->head->depth = 0;
  json_state->current = json_state->head;

  int last = 0;
  int i = 0;
  for (i = 0; i < args->lengths[0]; i++) {
    if (*(args->args[0] + i) == '.') {
      if (last == i) {
	last = i + 1;
      } else {
	json_state->current->el = calloc(i - last, sizeof(char));
	strncpy(json_state->current->el, args->args[0] + last, i - last);
	json_state->current->el_len = i - last;
	json_state->current->next = calloc(1, sizeof(struct json_el));
	json_state->current->next->prev = json_state->current;
	json_state->current = json_state->current->next;
	json_state->current->depth = 0;
	last = i + 1;
      }
    }
  }
  if (last != i) {
    json_state->current->el = calloc(i - last, sizeof(char));
    strncpy(json_state->current->el, args->args[0] + last, i - last);
    json_state->current->el_len = i - last;
  } else if (json_state->current != NULL) {
    struct json_el *to_free = json_state->current;
    json_state->current = to_free->prev;
    free(to_free);
    json_state->current->next = NULL;
  }

  struct json_el *cur = json_state->head;
  while (cur != NULL) {
    PARSE_TREE(cur->el);
    cur = cur->next;
  }
  PARSE_TREE_END();

  json_state->last = json_state->current;
  initid->ptr = (void *) json_state;

  return 0;
}

void json_extract_deinit(UDF_INIT *initid) {
  struct json_state *state = (struct json_state *) initid->ptr;
  if (state != NULL) {
    struct json_el *el = state->head;
    while (el != NULL) {
      struct json_el *n = el->next;
      free(el->el);
      free(el);
      el = n;
    }
    free(initid->ptr);
  }
}

char *json_extract(UDF_INIT *initid, UDF_ARGS *args, char *result,
		       unsigned long *length, char *is_null, char *error) {
  struct json_state *json_state = (struct json_state *) initid->ptr;
  json_state->done = 0;
  json_state->res = result;
  json_state->current = json_state->head;
  while (json_state->current != NULL) {
    json_state->current->depth = 0;
    json_state->current->arr_depth = 0;
    json_state->current = json_state->current->next;
  }
  json_state->current = json_state->head;

  yajl_handle hand = yajl_alloc(&callbacks, &parser_config, NULL, initid->ptr);
  yajl_status status;

  status = yajl_parse(hand, (const unsigned char *) args->args[1], args->lengths[1]);
  switch (status) {
  case yajl_status_error:
    *is_null = 1;
    goto bail;
  default: /* ok */;
  }

  if (status != yajl_status_ok && status != yajl_status_client_canceled) {
    status = yajl_parse_complete(hand);
    switch (status) {
    case yajl_status_error:
    case yajl_status_insufficient_data:
      *is_null = 1;
      goto bail;
    default: /* ok */;
    }
  }

  if (json_state->done == 1) {
    *is_null = 0;
    *length = json_state->res_len;
  } else {
    *is_null = 1;
  }

 bail:
  yajl_free(hand);
  return result;
}

