<template>
  <div class="root">
    <div class="top-editor">
      <div class="left">
        <div class="input-group">
          <span class="input-group-addon">Полное наименование</span>
          <input type="text" class="form-control" v-model="title">
        </div>
        <div class="input-group">
          <span class="input-group-addon">Краткое <small>(для создания направлений)</small></span>
          <input type="text" class="form-control" v-model="short_title">
        </div>
      </div>
      <div class="right">
        <div class="input-group">
          <span class="input-group-addon">Код</span>
          <input type="text" class="form-control" v-model="code">
        </div>
        <div class="input-group">
          <label class="input-group-addon" style="height: 34px;text-align: left;">
            <input type="checkbox" v-model="hide"/> Скрытие исследования
          </label>
        </div>
      </div>
    </div>
    <div class="content-editor">
      <div class="input-group">
        <span class="input-group-addon">Подготовка, кабинет</span>
        <textarea class="form-control noresize" v-autosize="info" v-model="info"></textarea>
      </div>
      <div v-for="group in ordered_groups" class="group">
        <div class="input-group">
          <span class="input-group-btn">
            <button class="btn btn-blue-nb lob" :disabled="is_first_group(group)" @click="dec_group_order(group)">
              <i class="glyphicon glyphicon-arrow-up"></i>
            </button>
          </span>
          <span class="input-group-btn">
            <button class="btn btn-blue-nb nob" :disabled="is_last_group(group)" @click="inc_group_order(group)">
              <i class="glyphicon glyphicon-arrow-down"></i>
            </button>
          </span>
          <span class="input-group-addon">Название группы</span>
          <input type="text" class="form-control" v-model="group.title">
        </div>
        <label>Отображать название <input v-model="group.show_title" type="checkbox"/></label><br/>
        <label>Скрыть группу <input v-model="group.hide" type="checkbox"/></label>
        <div>
          <strong>Поля ввода</strong>
        </div>
        <div v-for="row in ordered_fields(group)" class="field">
          <div class="field-inner">
            <div>
              <button class="btn btn-default btn-sm btn-block" :disabled="is_first_field(group, row)"
                      @click="dec_order(group, row)">
                <i class="glyphicon glyphicon-arrow-up"></i>
              </button>
              <button class="btn btn-default btn-sm btn-block" :disabled="is_last_field(group, row)"
                      @click="inc_order(group, row)">
                <i class="glyphicon glyphicon-arrow-down"></i>
              </button>
            </div>
            <div>
              <div class="input-group">
                <span class="input-group-addon">Название поля</span>
                <input type="text" class="form-control" v-model="row.title">
              </div>
              <div>
                <strong>Значение по умолчанию:</strong>
                <textarea v-model="row.default" :rows="row.lines" class="form-control" v-if="row.lines > 1"></textarea>
                <input v-model="row.default" class="form-control" v-else/>
              </div>
              <v-collapse-wrapper>
                <div class="header" v-collapse-toggle>
                  <a href="#" @click.prevent>
                    Шаблоны быстрого ввода (кол-во: {{ row.values_to_input.length }})
                  </a>
                </div>
                <div class="my-content" v-collapse-content>
                  <div class="input-group" style="margin-bottom: 5px">
                    <input type="text" v-model="row.new_value" class="form-control"
                           @keyup.enter="add_template_value(row)"
                           placeholder="Новый шаблон быстрого ввода"/>
                    <span class="input-group-btn"><button class="btn last btn-blue-nb" type="button"
                                                          :disabled="row.new_value === ''"
                                                          @click="add_template_value(row)">Добавить</button></span>
                  </div>
                  <div>
                    <div class="input-group" v-for="(v, i) in row.values_to_input" style="margin-bottom: 1px">
                  <span class="input-group-btn">
                  <button class="btn btn-blue-nb lob" :disabled="is_first_in_template(i)" @click="up_template(row, i)">
                    <i class="glyphicon glyphicon-arrow-up"></i>
                  </button>
                  </span>
                      <span class="input-group-btn">
                  <button class="btn btn-blue-nb nob" :disabled="is_last_in_template(row, i)"
                          @click="down_template(row, i)">
                    <i class="glyphicon glyphicon-arrow-down"></i>
                  </button>
                  </span>
                      <input class="form-control" type="text" v-model="row.values_to_input[i]"/>
                      <span class="input-group-btn">
                  <button class="btn btn-blue-nb" @click="remove_template(row, i)">
                    <i class="glyphicon glyphicon-remove"></i>
                  </button>
                  </span>
                    </div>
                  </div>
                </div>
              </v-collapse-wrapper>
            </div>
            <div>
              <label>
                <input type="checkbox" v-model="row.hide"/> скрыть поле
              </label>
              <label>
                Число строк<br/>для ввода:<br/>
                <input class="form-control" type="number" min="1" v-model.int="row.lines"/>
              </label>
            </div>
          </div>
        </div>
        <div>
          <button class="btn btn-blue-nb" @click="add_field(group)">Добавить поле</button>
        </div>
      </div>
      <div>
        <button class="btn btn-blue-nb" @click="add_group">Добавить группу</button>
      </div>
    </div>
    <div class="footer-editor">
      <button class="btn btn-blue-nb" @click="cancel">Отмена</button>
      <button class="btn btn-blue-nb" :disabled="!valid" @click="save">Сохранить</button>
    </div>
  </div>
</template>

<script>
  import construct_point from '../api/construct-point'
  import * as action_types from '../store/action-types'
  import VueCollapse from 'vue2-collapse'

  import Vue from 'vue'

  Vue.use(VueCollapse)

  export default {
    name: 'paraclinic-research-editor',
    props: {
      pk: {
        type: Number,
        required: true
      },
      department: {
        type: Number,
        required: true
      },
    },
    created() {
      this.load()
    },
    data() {
      return {
        title: '',
        short_title: '',
        code: '',
        info: '',
        hide: false,
        cancel_do: false,
        loaded_pk: -2,
        groups: [],
        template_add_types: [
          {sep: ' ', title: 'Пробел'},
          {sep: ', ', title: 'Запятая и пробел'},
          {sep: '; ', title: 'Точка с запятой (;) и пробел'},
          {sep: '. ', title: 'Точка и пробел'},
          {sep: '\n', title: 'Перенос строки'},
        ],
        has_unsaved: false
      }
    },
    watch: {
      pk() {
        this.load()
      },
      loaded_pk(n) {
        this.has_unsaved = false
      },
      groups: {
        handler(n, o) {
          if (o && o.length > 0) {
            this.has_unsaved = true
          }
        },
        deep: true
      }
    },
    mounted() {
      let vm = this
      $(window).on('beforeunload', function () {
        if (vm.has_unsaved && vm.loaded_pk > -2 && !vm.cancel_do)
          return 'Изменения, возможно, не сохранены. Вы уверены, что хотите покинуть страницу?'
      })
    },
    computed: {
      valid() {
        return this.norm_title.length > 0 && !this.cancel_do
      },
      norm_title() {
        return this.title.trim()
      },
      ordered_groups() {
        return this.groups.slice().sort(function (a, b) {
          return a.order === b.order ? 0 : +(a.order > b.order) || -1
        })
      },
      min_max_order_groups() {
        let min = 0
        let max = 0
        for (let row of this.groups) {
          if (min === 0) {
            min = row.order
          } else {
            min = Math.min(min, row.order)
          }
          max = Math.max(max, row.order)
        }
        return {min, max}
      },
    },
    methods: {
      is_first_in_template(i) {
        return i === 0
      },
      is_last_in_template(row, i) {
        return i === row.values_to_input.length - 1
      },
      up_template(row, i) {
        if (this.is_first_in_template(i))
          return
        let values = JSON.parse(JSON.stringify(row.values_to_input));
        [values[i - 1], values[i]] = [values[i], values[i - 1]]
        row.values_to_input = values
      },
      down_template(row, i) {
        if (this.is_last_in_template(row, i))
          return
        let values = JSON.parse(JSON.stringify(row.values_to_input));
        [values[i + 1], values[i]] = [values[i], values[i + 1]]
        row.values_to_input = values
      },
      remove_template(row, i) {
        if (row.values_to_input.length - 1 < i)
          return
        row.values_to_input.splice(i, 1)
      },
      add_template_value(row) {
        if (row.new_value === '')
          return
        row.values_to_input.push(row.new_value)
        row.new_value = ''
      },
      drag(row, ev) {
        // console.log(row, ev)
      },
      min_max_order(group) {
        let min = 0
        let max = 0
        for (let row of group.fields) {
          if (min === 0) {
            min = row.order
          } else {
            min = Math.min(min, row.order)
          }
          max = Math.max(max, row.order)
        }
        return {min, max}
      },
      ordered_fields(group) {
        return group.fields.slice().sort(function (a, b) {
          return a.order === b.order ? 0 : +(a.order > b.order) || -1
        })
      },
      inc_group_order(row) {
        if (row.order === this.min_max_order_groups.max)
          return
        let next_row = this.find_group_by_order(row.order + 1)
        if (next_row) {
          next_row.order--
        }
        row.order++
      },
      dec_group_order(row) {
        if (row.order === this.min_max_order_groups.min)
          return
        let prev_row = this.find_group_by_order(row.order - 1)
        if (prev_row) {
          prev_row.order++
        }
        row.order--
      },
      inc_order(group, row) {
        if (row.order === this.min_max_order(group).max)
          return
        let next_row = this.find_by_order(group, row.order + 1)
        if (next_row) {
          next_row.order--
        }
        row.order++
      },
      dec_order(group, row) {
        if (row.order === this.min_max_order(group).min)
          return
        let prev_row = this.find_by_order(group, row.order - 1)
        if (prev_row) {
          prev_row.order++
        }
        row.order--
      },
      find_by_order(group, order) {
        for (let row of group.fields) {
          if (row.order === order) {
            return row
          }
        }
        return false
      },
      find_group_by_order(order) {
        for (let row of this.groups) {
          if (row.order === order) {
            return row
          }
        }
        return false
      },
      is_first_group(group) {
        return group.order === this.min_max_order_groups.min
      },
      is_last_group(group) {
        return group.order === this.min_max_order_groups.max
      },
      is_first_field(group, row) {
        return row.order === this.min_max_order(group).min
      },
      is_last_field(group, row) {
        return row.order === this.min_max_order(group).max
      },
      add_field(group) {
        let order = 0
        for (let row of group.fields) {
          order = Math.max(order, row.order)
        }
        group.fields.push({
          pk: -1,
          order: order + 1,
          title: '',
          default: '',
          values_to_input: [],
          new_value: '',
          hide: false,
          lines: 3
        })
      },
      add_group() {
        let order = 0
        for (let row of this.groups) {
          order = Math.max(order, row.order)
        }
        let g = {pk: -1, order: order + 1, title: '', fields: [], show_title: true, hide: false}
        this.add_field(g)
        this.groups.push(g)
      },
      load() {
        this.title = ''
        this.short_title = ''
        this.code = ''
        this.info = ''
        this.hide = false
        this.groups = []
        if (this.pk >= 0) {
          let vm = this
          vm.$store.dispatch(action_types.INC_LOADING).then()
          construct_point.researchDetails(vm.pk).then(data => {
            vm.title = data.title
            vm.short_title = data.short_title
            vm.code = data.code
            vm.info = data.info.replace(/<br\/>/g, '\n').replace(/<br>/g, '\n')
            vm.hide = data.hide
            vm.loaded_pk = vm.pk
            vm.groups = data.groups
            if (vm.groups.length === 0) {
              vm.add_group()
            }
          }).finally(() => {
            vm.$store.dispatch(action_types.DEC_LOADING).then()
          })
        } else {
          this.add_group()
        }
      },
      cancel() {
        if (this.has_unsaved && !confirm('Изменения, возможно, не сохранены. Вы уверены, что хотите отменить редактирование?')) {
          return
        }
        this.cancel_do = true
        this.$root.$emit('research-editor:cancel')
      },
      save() {
        let vm = this
        vm.$store.dispatch(action_types.INC_LOADING).then()
        construct_point.updateResearch(vm.pk, vm.department, vm.title, vm.short_title, vm.code, vm.info.replace(/\n/g, '<br/>').replace(/<br>/g, '<br/>'), vm.hide, vm.groups).then(() => {
          vm.has_unsaved = false
          okmessage('Сохранено')
          this.cancel()
        }).finally(() => {
          vm.$store.dispatch(action_types.DEC_LOADING).then()
        })
      }
    }
  }
</script>

<style scoped lang="scss">
  .top-editor {
    display: flex;
    flex: 0 0 68px;

    .left, .right {
      flex: 0 0 50%
    }

    .left {
      border-right: 1px solid #96a0ad;
    }

    .input-group-addon {
      border-top: none;
      border-left: none;
      border-radius: 0;
    }

    .form-control {
      border-top: none;
      border-radius: 0;
    }

    .input-group > .form-control:last-child {
      border-right: none;
    }
  }

  .content-editor {
    height: 100%;
  }

  .footer-editor {
    flex: 0 0 34px;
    display: flex;
    justify-content: flex-end;
    background-color: #f4f4f4;

    .btn {
      border-radius: 0;
    }
  }

  .top-editor, .content-editor, .footer-editor {
    align-self: stretch;
  }

  .root {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    align-content: stretch;
  }

  .content-editor {
    padding: 5px;
    overflow-y: auto;
  }

  .group {
    padding: 5px;
    margin: 5px;
    border-radius: 5px;
    background: #f0f0f0;
  }

  .field {
    padding: 5px;
    margin: 5px;
    border-radius: 5px;
    background: #fff;
    color: #000;
  }

  .field-inner {
    display: flex;
    flex-direction: row;
    align-items: stretch;
  }

  .field-inner > div {
    align-self: stretch;
    textarea {
      resize: none;
    }

    &:nth-child(1) {
      flex: 0 0 35px;
      padding-right: 5px;
    }
    &:nth-child(2) {
      width: 100%;
    }
    &:nth-child(3) {
      width: 140px;
      padding-left: 5px;
      padding-right: 5px;
      white-space: nowrap;
      label {
        display: block;
        margin-bottom: 2px;
        width: 100%;
        input[type="number"] {
          width: 100%;
        }
      }
    }
  }

  .lob {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
  }

  .nob {
    border-radius: 0;
  }

  /deep/ .v-collapse-content-end {
    max-height: 10000px !important;
  }
</style>
